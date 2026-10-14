import 'package:flutter/foundation.dart';

import '../models/app_user.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import 'device_id_store.dart';
import 'token_store.dart';

enum AuthStatus { unknown, signedOut, codeRequired, signedIn }

/// Who is signed in, shared across screens.
class AuthState extends ChangeNotifier {
  AuthState({
    required ApiClient api,
    required this._store,
    required this._deviceIds,
    this.onSessionCleared,
  }) : _api = api,
       _auth = AuthService(api);

  /// Called when the user logs out or the server ends the session (401), to
  /// forget data saved on the device for this account. Not called when a
  /// launch merely fails to reach the server.
  final Future<void> Function()? onSessionCleared;

  final ApiClient _api;
  final TokenStore _store;
  final DeviceIdStore _deviceIds;
  final AuthService _auth;

  AuthStatus status = AuthStatus.unknown;

  /// Null when the app was opened offline with a saved session.
  AppUser? user;

  /// The emailed-code step in progress, while [status] is codeRequired.
  CodeChallenge? challenge;

  /// Restores a saved session on launch.
  Future<void> restore() async {
    final token = await _store.read();
    if (token == null) return _setSignedOut();
    _api.token = token;
    try {
      user = await _auth.me();
      status = AuthStatus.signedIn;
      notifyListeners();
    } on ApiException catch (e) {
      if (e.statusCode == null) {
        // Offline: the saved session can't be checked, so keep it and open
        // the app with what's saved on the phone (#102). The first request
        // that reaches the server signs out if the token has ended (401).
        status = AuthStatus.signedIn;
        notifyListeners();
        return;
      }
      if (e.statusCode == 401) {
        await _store.clear();
        await onSessionCleared?.call();
      }
      _api.token = null;
      _setSignedOut();
    }
  }

  Future<void> register(String email, String password) async => _handle(
    await _auth.register(email, password, deviceId: await _deviceIds.id()),
  );

  Future<void> login(String email, String password) async => _handle(
    await _auth.login(email, password, deviceId: await _deviceIds.id()),
  );

  /// Finishes signing in with the emailed code.
  Future<void> verifyCode(String code, {bool rememberDevice = true}) async {
    final pending = challenge;
    if (pending == null) return;
    await _signIn(
      await _auth.verify(
        pending,
        code,
        deviceId: await _deviceIds.id(),
        remember: rememberDevice,
      ),
    );
  }

  /// Emails a new code; returns the refreshed challenge.
  Future<CodeChallenge?> resendCode() async {
    final pending = challenge;
    if (pending == null) return null;
    challenge = await _auth.resend(pending);
    notifyListeners();
    return challenge;
  }

  /// Back to the login form ("use a different account").
  void cancelChallenge() => _setSignedOut();

  Future<void> logout() async {
    try {
      await _auth.logout();
    } on ApiException {
      // The token is discarded locally either way.
    }
    await _store.clear();
    await onSessionCleared?.call();
    _api.token = null;
    _setSignedOut();
  }

  /// The server rejected the token (401): forget it without calling the
  /// server again, so the app shows the login screen.
  Future<void> sessionExpired() async {
    await _store.clear();
    await onSessionCleared?.call();
    _api.token = null;
    _setSignedOut();
  }

  Future<void> _handle(LoginOutcome outcome) async {
    switch (outcome) {
      case SignedIn(:final result):
        await _signIn(result);
      case CodeRequired(challenge: final c):
        challenge = c;
        status = AuthStatus.codeRequired;
        notifyListeners();
    }
  }

  Future<void> _signIn(AuthResult result) async {
    await _store.write(result.token);
    _api.token = result.token;
    user = result.user;
    challenge = null;
    status = AuthStatus.signedIn;
    notifyListeners();
  }

  void _setSignedOut() {
    user = null;
    challenge = null;
    status = AuthStatus.signedOut;
    notifyListeners();
  }
}
