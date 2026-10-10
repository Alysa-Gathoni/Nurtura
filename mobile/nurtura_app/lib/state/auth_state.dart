import 'package:flutter/foundation.dart';

import '../models/app_user.dart';
import '../services/api_client.dart';
import '../services/auth_service.dart';
import 'token_store.dart';

enum AuthStatus { unknown, signedOut, signedIn }

/// Who is signed in, shared across screens.
class AuthState extends ChangeNotifier {
  AuthState({required ApiClient api, required this._store})
    : _api = api,
      _auth = AuthService(api);

  final ApiClient _api;
  final TokenStore _store;
  final AuthService _auth;

  AuthStatus status = AuthStatus.unknown;
  AppUser? user;

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
      if (e.statusCode == 401) await _store.clear();
      _api.token = null;
      _setSignedOut();
    }
  }

  Future<void> register(String email, String password) async =>
      _signIn(await _auth.register(email, password));

  Future<void> login(String email, String password) async =>
      _signIn(await _auth.login(email, password));

  Future<void> logout() async {
    try {
      await _auth.logout();
    } on ApiException {
      // The token is discarded locally either way.
    }
    await _store.clear();
    _api.token = null;
    _setSignedOut();
  }

  /// The server rejected the token (401): forget it without calling the
  /// server again, so the app shows the login screen.
  Future<void> sessionExpired() async {
    await _store.clear();
    _api.token = null;
    _setSignedOut();
  }

  Future<void> _signIn(AuthResult result) async {
    await _store.write(result.token);
    _api.token = result.token;
    user = result.user;
    status = AuthStatus.signedIn;
    notifyListeners();
  }

  void _setSignedOut() {
    user = null;
    status = AuthStatus.signedOut;
    notifyListeners();
  }
}
