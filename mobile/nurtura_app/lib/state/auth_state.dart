import 'package:flutter/foundation.dart';

import '../models/app_user.dart';
import '../models/privacy_notice.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../services/google_auth.dart';
import 'device_id_store.dart';
import 'preferences.dart';
import 'token_store.dart';

enum AuthStatus { unknown, signedOut, codeRequired, signedIn }

/// Who is signed in, shared across screens.
class AuthState extends ChangeNotifier {
  AuthState({
    required ApiClient api,
    required this._store,
    required this._deviceIds,
    this.onSessionCleared,
    Preferences? preferences,
    this._google,
  }) : _api = api,
       _prefs = preferences,
       _auth = AuthService(api);

  /// Where the signed-in user's role is kept, so an administrator who opens
  /// the app offline still lands on the admin screens (#123).
  static const roleKey = 'nurtura.role';

  /// Called when the user logs out or the server ends the session (401), to
  /// forget data saved on the device for this account. Not called when a
  /// launch merely fails to reach the server.
  final Future<void> Function()? onSessionCleared;

  final ApiClient _api;
  final TokenStore _store;
  final DeviceIdStore _deviceIds;
  final AuthService _auth;
  final Preferences? _prefs;
  final GoogleIdTokens? _google;

  /// Whether "Continue with Google" is offered (#130).
  bool get googleAvailable => _google != null;
  String? _savedRole;

  AuthStatus status = AuthStatus.unknown;

  /// Administrators get the admin screens; everyone else the caregiver app.
  bool get isAdministrator =>
      (user?.role ?? _savedRole) == AppUser.administratorRole;

  /// A caregiver who hasn't agreed to the current privacy notice sees it
  /// before anything else (#136). Unknown offline, so not asked then.
  bool get needsPrivacyConsent => user?.privacyConsentRequired ?? false;

  Future<PrivacyNotice> privacyNotice() => _auth.privacyNotice();

  /// Records agreement to the notice [version] shown; throws [ApiException].
  Future<void> agreeToPrivacy(String version) async {
    user = await _auth.agreeToPrivacy(version);
    notifyListeners();
  }

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
      await _rememberRole(user!.role);
      status = AuthStatus.signedIn;
      notifyListeners();
    } on ApiException catch (e) {
      if (e.statusCode == null) {
        _savedRole = await _prefs?.getString(roleKey);
        // Offline: the saved session can't be checked, so keep it and open
        // the app with what's saved on the phone (#102). The first request
        // that reaches the server signs out if the token has ended (401).
        status = AuthStatus.signedIn;
        notifyListeners();
        return;
      }
      if (e.statusCode == 401) {
        await _store.clear();
        await _forgetRole();
        await onSessionCleared?.call();
      }
      _api.token = null;
      _setSignedOut();
    }
  }

  Future<void> _rememberRole(String role) async {
    _savedRole = role;
    await _prefs?.setString(roleKey, role);
  }

  Future<void> _forgetRole() async {
    _savedRole = null;
    await _prefs?.remove(roleKey);
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

  /// Signs in or registers with the Google account the person picks (#130).
  /// Does nothing if they close Google's chooser.
  Future<void> continueWithGoogle() async {
    final google = _google;
    if (google == null) return;
    final token = await google.idToken();
    if (token == null) return;
    try {
      await _signIn(await _auth.google(token, deviceId: await _deviceIds.id()));
    } on ApiException {
      // Let them pick a different account next time.
      await google.signOut();
      rethrow;
    }
  }

  /// Emails a password-reset code (#126).
  Future<CodeChallenge> requestPasswordReset(String email) =>
      _auth.requestPasswordReset(email);

  Future<CodeChallenge> resendPasswordReset(CodeChallenge challenge) =>
      _auth.resendPasswordReset(challenge);

  /// Sets the new password and signs in on this phone.
  Future<void> resetPassword(
    CodeChallenge challenge,
    String code,
    String newPassword, {
    bool rememberDevice = true,
  }) async {
    await _signIn(
      await _auth.confirmPasswordReset(
        challenge,
        code,
        newPassword,
        deviceId: await _deviceIds.id(),
        remember: rememberDevice,
      ),
    );
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
    await _forgetRole();
    await onSessionCleared?.call();
    await _google?.signOut();
    _api.token = null;
    _setSignedOut();
  }

  /// The server rejected the token (401): forget it without calling the
  /// server again, so the app shows the login screen.
  Future<void> sessionExpired() async {
    await _store.clear();
    await _forgetRole();
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
    await _rememberRole(result.user.role);
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
