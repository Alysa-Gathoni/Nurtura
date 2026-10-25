import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../models/child_profile.dart';
import '../services/api_client.dart';
import '../services/child_service.dart';
import 'preferences.dart';

/// The signed-in caregiver's children, shared across screens.
///
/// A copy of the list is kept on the phone so the app can open offline
/// (#102); [clearSaved] removes it when the session ends.
class ChildrenState extends ChangeNotifier {
  ChildrenState(ApiClient api, this._prefs) : _service = ChildService(api);

  static const savedKey = 'nurtura.children';

  final ChildService _service;
  final Preferences _prefs;

  /// The list on screen is the saved copy: the server couldn't be reached.
  bool offline = false;

  List<ChildProfile> children = const [];
  int? _selectedId;
  bool loading = false;
  bool loaded = false;
  ApiException? error;

  /// The child the Today, Progress and Milestones tabs are about: the one
  /// last picked, else the first.
  ChildProfile? get selected {
    if (children.isEmpty) return null;
    return children.firstWhere(
      (c) => c.id == _selectedId,
      orElse: () => children.first,
    );
  }

  void select(ChildProfile child) {
    if (_selectedId == child.id) return;
    _selectedId = child.id;
    notifyListeners();
  }

  Future<void> load() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      children = await _service.list();
      loaded = true;
      offline = false;
      await _save();
    } on ApiException catch (e) {
      // No response at all: fall back to the saved list, if there is one.
      final saved = e.statusCode == null ? await _readSaved() : null;
      if (saved != null) {
        children = saved;
        loaded = true;
        offline = true;
      } else {
        error = e;
      }
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  /// Saves a new child; throws [ApiException] with field errors on failure.
  Future<ChildProfile> create({
    required String name,
    required DateTime dateOfBirth,
    List<String> interests = const [],
    List<String> concerns = const [],
  }) async {
    final child = await _service.create(
      name: name,
      dateOfBirth: dateOfBirth,
      interests: interests,
      concerns: concerns,
    );
    children = [...children, child]..sort((a, b) => a.name.compareTo(b.name));
    _selectedId = child.id;
    notifyListeners();
    await _save();
    return child;
  }

  /// Saves changes to a child; throws [ApiException] with field errors.
  ///
  /// The child's ideas were picked for the old profile, so the Today tab is
  /// told to ask for a fresh batch ([takeIdeasOutOfDate]).
  Future<ChildProfile> update(
    ChildProfile child, {
    required String name,
    required DateTime dateOfBirth,
    required List<String> interests,
    required List<String> concerns,
  }) async {
    final updated = await _service.update(
      child.id,
      name: name,
      dateOfBirth: dateOfBirth,
      interests: interests,
      concerns: concerns,
    );
    children = [for (final c in children) c.id == updated.id ? updated : c]
      ..sort((a, b) => a.name.compareTo(b.name));
    _ideasOutOfDate.add(updated.id);
    notifyListeners();
    await _save();
    return updated;
  }

  /// Deletes a child's profile, with its milestones, ideas and ratings.
  Future<void> delete(ChildProfile child) async {
    await _service.delete(child.id);
    children = [
      for (final c in children)
        if (c.id != child.id) c,
    ];
    if (_selectedId == child.id) _selectedId = null;
    _ideasOutOfDate.remove(child.id);
    notifyListeners();
    await _save();
  }

  final _ideasOutOfDate = <int>{};

  /// True, once, if the child's profile was edited since their ideas were
  /// last fetched.
  bool takeIdeasOutOfDate(int childId) => _ideasOutOfDate.remove(childId);

  Future<void> _save() => _prefs.setString(
    savedKey,
    jsonEncode([for (final c in children) c.toJson()]),
  );

  Future<List<ChildProfile>?> _readSaved() async {
    final raw = await _prefs.getString(savedKey);
    if (raw == null) return null;
    try {
      return [
        for (final c in jsonDecode(raw) as List)
          ChildProfile.fromJson(c as Map<String, dynamic>),
      ];
    } on Object {
      return null; // unreadable: as if nothing was saved
    }
  }

  /// Forgets the saved list (logout or an ended session).
  Future<void> clearSaved() => _prefs.remove(savedKey);

  void clear() {
    children = const [];
    _selectedId = null;
    _ideasOutOfDate.clear();
    loaded = false;
    offline = false;
    error = null;
    notifyListeners();
  }
}
