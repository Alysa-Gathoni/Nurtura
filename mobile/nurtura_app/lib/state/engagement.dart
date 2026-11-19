import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../utils/dates.dart';
import 'preferences.dart';

/// The week streak (#244): weeks in a row (Monday to Sunday) in which the
/// caregiver looked at their child's ideas, which come as a weekly plan.
/// The days are stored and grouped into weeks. Kept only on this phone and
/// cleared on logout. It counts the caregiver's own visits and never
/// compares children.
class EngagementState extends ChangeNotifier {
  EngagementState(this._prefs, {DateTime Function()? clock})
    : _clock = clock ?? today;

  static const _key = 'nurtura.checkInDays';
  static const _keepDays = 400;

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

  /// The Mondays of the weeks with at least one check-in.
  Set<DateTime> get _weeks => {for (final d in _days) weekOf(d)};

  static DateTime _weekBefore(DateTime monday) =>
      DateTime(monday.year, monday.month, monday.day - 7);

  bool get checkedInThisWeek => _weeks.contains(weekOf(_clock()));

  /// Consecutive weeks up to this one (or up to last week, if this week
  /// hasn't been checked yet, so the streak isn't lost on a Monday).
  int get streak {
    final weeks = _weeks;
    var week = weekOf(_clock());
    if (!weeks.contains(week)) week = _weekBefore(week);
    var count = 0;
    while (weeks.contains(week)) {
      count++;
      week = _weekBefore(week);
    }
    return count;
  }

  /// The longest run of consecutive weeks on record.
  int get bestStreak {
    final sorted = _weeks.toList()..sort();
    var best = 0;
    var run = 0;
    DateTime? previous;
    for (final week in sorted) {
      run = previous != null && _weekBefore(week) == previous ? run + 1 : 1;
      if (run > best) best = run;
      previous = week;
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
