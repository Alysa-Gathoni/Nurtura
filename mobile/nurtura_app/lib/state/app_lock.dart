import 'package:flutter/foundation.dart';

import '../services/biometrics.dart';
import 'preferences.dart';

/// "Unlock with fingerprint" (#150): whether it's on, and whether the app
/// is locked right now.
///
/// It only guards the sign-in already saved on this phone; the server is
/// unchanged. It locks when the app opens and when it comes back after
/// [relockAfter] away. Logging out turns it off ([forget]), so the next
/// account on the phone doesn't inherit it.
class AppLock extends ChangeNotifier {
  AppLock(this._biometrics, this._prefs, {DateTime Function()? clock})
    : _clock = clock ?? DateTime.now;

  static const prefKey = 'nurtura.fingerprintLock';
  static const relockAfter = Duration(minutes: 1);

  final Biometrics _biometrics;
  final Preferences _prefs;
  final DateTime Function() _clock;

  /// The phone has a fingerprint (or face) set up.
  bool available = false;
  bool enabled = false;
  bool locked = false;

  /// [load] has finished, so the gate knows whether to lock (no flash of
  /// the app before the lock screen).
  bool loaded = false;

  /// Why the last check couldn't run, for the lock screen.
  String? error;
  DateTime? _leftAt;

  /// Reads the setting at launch; locks if it's on.
  Future<void> load() async {
    available = await _biometrics.available();
    enabled = available && await _prefs.getString(prefKey) == 'on';
    locked = enabled;
    loaded = true;
    notifyListeners();
  }

  /// Turns the lock on after one successful scan; false if it wasn't.
  Future<bool> enable() async {
    final ok = await _check('Confirm your fingerprint to lock Nurtura');
    if (ok) {
      await _prefs.setString(prefKey, 'on');
      enabled = true;
    }
    notifyListeners();
    return ok;
  }

  Future<void> disable() async {
    await _prefs.remove(prefKey);
    enabled = false;
    locked = false;
    notifyListeners();
  }

  /// The lock screen's scan.
  Future<void> unlock() async {
    if (await _check('Unlock Nurtura')) locked = false;
    notifyListeners();
  }

  /// The session ended (log out, account deleted, 401): turn the lock off.
  Future<void> forget() => disable();

  void appLeft() => _leftAt = _clock();

  void appReturned() {
    final left = _leftAt;
    _leftAt = null;
    if (enabled &&
        !locked &&
        left != null &&
        _clock().difference(left) >= relockAfter) {
      locked = true;
      notifyListeners();
    }
  }

  Future<bool> _check(String reason) async {
    error = null;
    try {
      return await _biometrics.check(reason);
    } on BiometricsError catch (e) {
      error = e.message;
      return false;
    }
  }
}
