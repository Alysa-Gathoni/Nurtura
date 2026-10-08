import '../models/app_user.dart';
import 'api_client.dart';

class AuthResult {
  const AuthResult(this.token, this.user);

  final String token;
  final AppUser user;
}

/// Token authentication against /api/auth/.
///
/// Caregivers sign in with their email, so the email (lower-cased) is also
/// their username on the backend.
class AuthService {
  AuthService(this._api);

  final ApiClient _api;

  Future<AuthResult> register(String email, String password) async {
    final normalized = _normalize(email);
    try {
      final data = await _api.post('/api/auth/register/', {
        'username': normalized,
        'email': normalized,
        'password': password,
      });
      return _result(data);
    } on ApiException catch (e) {
      // The username is the email, so a duplicate is reported on both fields;
      // show it once, on the email field.
      final fields = Map.of(e.fieldErrors);
      final usernameError = fields.remove('username');
      if (usernameError != null && !fields.containsKey('email')) {
        fields['email'] = ['An account with this email already exists.'];
      }
      throw ApiException(
        e.message,
        statusCode: e.statusCode,
        fieldErrors: fields,
      );
    }
  }

  Future<AuthResult> login(String email, String password) async {
    try {
      final data = await _api.post('/api/auth/login/', {
        'username': _normalize(email),
        'password': password,
      });
      return _result(data);
    } on ApiException catch (e) {
      if (e.statusCode == 400) {
        throw ApiException(
          "That email and password don't match an account.",
          statusCode: 400,
        );
      }
      rethrow;
    }
  }

  Future<void> logout() => _api.post('/api/auth/logout/');

  Future<AppUser> me() async =>
      AppUser.fromJson(await _api.get('/api/auth/me/') as Map<String, dynamic>);

  static String _normalize(String email) => email.trim().toLowerCase();

  static AuthResult _result(dynamic data) {
    final json = data as Map<String, dynamic>;
    return AuthResult(
      json['token'] as String,
      AppUser.fromJson(json['user'] as Map<String, dynamic>),
    );
  }
}
