import 'package:flutter/foundation.dart';

import '../models/child_profile.dart';
import '../services/api_client.dart';
import '../services/child_service.dart';

/// The signed-in caregiver's children, shared across screens.
class ChildrenState extends ChangeNotifier {
  ChildrenState(ApiClient api) : _service = ChildService(api);

  final ChildService _service;

  List<ChildProfile> children = const [];
  bool loading = false;
  bool loaded = false;
  ApiException? error;

  Future<void> load() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      children = await _service.list();
      loaded = true;
    } on ApiException catch (e) {
      error = e;
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
    notifyListeners();
    return child;
  }

  void clear() {
    children = const [];
    loaded = false;
    error = null;
    notifyListeners();
  }
}
