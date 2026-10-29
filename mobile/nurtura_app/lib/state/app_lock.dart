import 'package:flutter/foundation.dart';

import '../services/api_client.dart';
import '../services/biometrics.dart';
import 'auth_state.dart';
import 'fingerprint_store.dart';

/// Fingerprint log-in and lock (#150).
///
/// Turning it on gets this phone a key from the server, kept in secure
/// storage. While signed in, the app locks when it opens and when it comes
/// back after [relockAfter] away. After logging out, the login screen
/// offers "Log in with fingerprint", which sends the key once the phone's
/// own check passes. The fingerprint never reaches Nurtura.
class AppLock extends ChangeNotifier {
  AppLock(
    this._biometrics,
    this._store,
    this._auth, {
    DateTime Function()? clock,
  }) : _clock = clock ?? DateTime.now;

  static const relockAfter = Duration(minutes: 1);

  final Biometrics _biometrics;
  final FingerprintStore _store;
  final AuthState _auth;
  final DateTime Function() _clock;

  /// The phone has a fingerprint (or face) set up.
  bool available = false;

  /// The account this phone can log in to with a fingerprint.
  SavedFingerprint? saved;
  bool locked = false;

  /// [load] has finished, so the gate knows whether to lock (no flash of
  /// the app before the lock screen).
  bool loaded = false;

  /// Why the last check or log-in didn't work, for the screen.
  String? error;

  bool _offerAtLaunch = false;
  DateTime? _leftAt;

  bool get canLogIn => available && saved != null;

  /// On for the signed-in account (unknown offline: then assume so).
  bool get enabled {
    final s = saved;
    if (!available || s == null) return false;
    final email = _auth.user?.email;
    return email == null || email.toLowerCase() == s.email.toLowerCase();
  }

  /// Reads the setting at launch; locks a saved session if it's on.
  Future<void> load() async {
    available = await _biometrics.available();
    saved = await _store.read();
    locked = canLogIn;
    _offerAtLaunch = canLogIn;
    loaded = true;
    notifyListeners();
  }

  /// The login screen asks for the fingerprint once, when the app opens
  /// (not after the person logged out on purpose).
  bool takeLaunchOffer() {
    final offer = _offerAtLaunch && canLogIn;
    _offerAtLaunch = false;
    return offer;
  }

  /// Turns it on for the signed-in account; false (with [error]) if not.
  Future<bool> enable() async {
    final email = _auth.user?.email;
    if (email == null) {
      error = 'Connect to the internet to turn this on.';
      notifyListeners();
      return false;
    }
    if (!await _check('Confirm your fingerprint for Nurtura')) {
      notifyListeners();
      return false;
    }
    try {
      final key = await _auth.issueFingerprintKey();
      saved = SavedFingerprint(email: email, key: key);
      await _store.write(saved!);
      return true;
    } on ApiException catch (e) {
      error = e.message;
      return false;
    } finally {
      notifyListeners();
    }
  }

  /// Turns it off on this phone, and revokes the key when online.
  Future<void> disable() async {
    try {
      await _auth.revokeFingerprintKey();
    } on ApiException {
      // Offline: forgotten here; the server's copy is replaced next time.
    }
    await _forget();
  }

  /// The lock screen's scan.
  Future<void> unlock() async {
    if (await _check('Unlock Nurtura')) {
      locked = false;
      // The session was already open, so a later log-out isn't "launch".
      _offerAtLaunch = false;
    }
    notifyListeners();
  }

  /// The login screen's "Log in with fingerprint".
  Future<void> logIn() async {
    final s = saved;
    if (s == null || !await _check('Log in to Nurtura')) {
      notifyListeners();
      return;
    }
    try {
      await _auth.logInWithFingerprintKey(s.key);
      locked = false;
    } on ApiException catch (e) {
      error = e.message;
      // Revoked (password reset, turned off elsewhere): stop offering it.
      if (e.fieldErrors.containsKey('key')) await _forget();
    }
    notifyListeners();
  }

  /// Logged out: unlocked, but fingerprint log-in stays for next time.
  void sessionEnded() {
    locked = false;
    _leftAt = null;
    _offerAtLaunch = false;
    error = null;
    notifyListeners();
  }

  /// The account was deleted: its key went with it.
  Future<void> accountDeleted() => _forget();

  void appLeft() => _leftAt = _clock();

  void appReturned() {
    final left = _leftAt;
    _leftAt = null;
    if (_auth.status == AuthStatus.signedIn &&
        enabled &&
        !locked &&
        left != null &&
        _clock().difference(left) >= relockAfter) {
      locked = true;
      notifyListeners();
    }
  }

  Future<void> _forget() async {
    await _store.clear();
    saved = null;
    locked = false;
    notifyListeners();
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
