import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../utils/dates.dart';
import 'preferences.dart';

/// The day streak: days in a row on which the caregiver looked at their
/// child's ideas. Kept only on this phone and cleared on logout. It counts
/// the caregiver's own visits and never compares children.
class EngagementState extends ChangeNotifier {
  EngagementState(this._prefs, {DateTime Function()? clock})
    : _clock = clock ?? today;

  static const _key = 'nurtura.checkInDays';
  static const _keepDays = 60;

  final Preferences _prefs;
  final DateTime Function() _clock;
  Set<DateTime> _days = {};

  Future<void> load() async {
    final raw = await _prefs.getString(_key);
    if (raw == null) return;
    try {
      _days = {
        for (final d in jsonDecode(raw) as List) DateTime.parse(d as String),
      };
      notifyListeners();
    } on Object {
      _days = {}; // unreadable: start again
    }
  }

  /// Marks today as a day the ideas were checked.
  Future<void> checkIn() async {
    final day = _dateOnly(_clock());
    if (_days.contains(day)) return;
    _days = {..._days.where((d) => day.difference(d).inDays < _keepDays), day};
    notifyListeners();
    await _prefs.setString(
      _key,
      jsonEncode([for (final d in _days) apiDate(d)]),
    );
  }

  bool get checkedInToday => _days.contains(_dateOnly(_clock()));

  /// Consecutive days up to today (or up to yesterday, if today hasn't
  /// been checked yet, so the streak isn't lost first thing in the morning).
  int get streak {
    var day = _dateOnly(_clock());
    if (!_days.contains(day)) day = day.subtract(const Duration(days: 1));
    var count = 0;
    while (_days.contains(day)) {
      count++;
      day = day.subtract(const Duration(days: 1));
    }
    return count;
  }

  /// The longest run of consecutive days on record.
  int get bestStreak {
    final sorted = _days.toList()..sort();
    var best = 0;
    var run = 0;
    DateTime? previous;
    for (final day in sorted) {
      run = previous != null && day.difference(previous).inDays == 1
          ? run + 1
          : 1;
      if (run > best) best = run;
      previous = day;
    }
    return best;
  }

  Future<void> clear() async {
    _days = {};
    notifyListeners();
    await _prefs.remove(_key);
  }

  static DateTime _dateOnly(DateTime d) => DateTime(d.year, d.month, d.day);
}
