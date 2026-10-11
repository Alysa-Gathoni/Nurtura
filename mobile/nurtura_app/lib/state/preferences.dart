import 'package:shared_preferences/shared_preferences.dart';

/// Small key-value storage on the device for app preferences (theme) and
/// light engagement data (the day streak). Not for anything secret.
abstract class Preferences {
  Future<String?> getString(String key);
  Future<void> setString(String key, String value);
  Future<void> remove(String key);
}

/// [Preferences] in shared_preferences.
class SharedPrefsPreferences implements Preferences {
  Future<SharedPreferences> get _prefs => SharedPreferences.getInstance();

  @override
  Future<String?> getString(String key) async => (await _prefs).getString(key);

  @override
  Future<void> setString(String key, String value) async =>
      (await _prefs).setString(key, value);

  @override
  Future<void> remove(String key) async => (await _prefs).remove(key);
}

/// In-memory [Preferences] for tests.
class MemoryPreferences implements Preferences {
  MemoryPreferences([Map<String, String>? values]) : values = values ?? {};

  final Map<String, String> values;

  @override
  Future<String?> getString(String key) async => values[key];

  @override
  Future<void> setString(String key, String value) async => values[key] = value;

  @override
  Future<void> remove(String key) async => values.remove(key);
}
