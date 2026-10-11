import 'package:flutter/material.dart';

import 'preferences.dart';

/// Light, dark, or following the phone (the default), remembered on the
/// device.
class ThemeState extends ChangeNotifier {
  ThemeState(this._prefs);

  static const _key = 'nurtura.themeMode';

  final Preferences _prefs;
  ThemeMode mode = ThemeMode.system;

  Future<void> load() async {
    final saved = await _prefs.getString(_key);
    final match = ThemeMode.values.where((m) => m.name == saved);
    if (match.isNotEmpty && match.first != mode) {
      mode = match.first;
      notifyListeners();
    }
  }

  Future<void> set(ThemeMode value) async {
    if (value == mode) return;
    mode = value;
    notifyListeners();
    await _prefs.setString(_key, value.name);
  }
}
