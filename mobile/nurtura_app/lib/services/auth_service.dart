import '../models/app_user.dart';
import '../models/privacy_notice.dart';
import 'api_client.dart';

class AuthResult {
  const AuthResult(this.token, this.user);

  final String token;
  final AppUser user;
}

/// An emailed code is needed before signing in (#91).
class CodeChallenge {
  const CodeChallenge({
    required this.id,
    required this.emailHint,
    required this.expiresIn,
    required this.resendAfter,
  });

  factory CodeChallenge.fromJson(Map<String, dynamic> json) => CodeChallenge(
    id: json['challenge'] as String,
    emailHint: json['email_hint'] as String? ?? 'your email address',
    expiresIn: Duration(seconds: json['expires_in'] as int? ?? 600),
    resendAfter: Duration(seconds: json['resend_after'] as int? ?? 30),
  );

  final String id;

  /// Where the code was sent, partly hidden: "w***@example.com".
  final String emailHint;
  final Duration expiresIn;
  final Duration resendAfter;
}

/// The result of a password step: signed in (a trusted phone), or a code
/// is needed.
sealed class LoginOutcome {
  const LoginOutcome();
}

class SignedIn extends LoginOutcome {
  const SignedIn(this.result);

  final AuthResult result;
}

class CodeRequired extends LoginOutcome {
  const CodeRequired(this.challenge);

  final CodeChallenge challenge;
}

/// Token authentication against /api/auth/, with the emailed second step.
///
/// Caregivers sign in with their email, so the email (lower-cased) is also
/// their username on the backend.
class AuthService {
  AuthService(this._api);

  final ApiClient _api;

  Future<LoginOutcome> register(
    String email,
    String password, {
    String? deviceId,
  }) async {
    final normalized = _normalize(email);
    try {
      final data = await _api.post('/api/auth/register/', {
        'username': normalized,
        'email': normalized,
        'password': password,
        'device_id': ?deviceId,
      });
      return _outcome(data);
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

  Future<LoginOutcome> login(
    String email,
    String password, {
    String? deviceId,
  }) async {
    try {
      final data = await _api.post('/api/auth/login/', {
        'username': _normalize(email),
        'password': password,
        'device_id': ?deviceId,
      });
      return _outcome(data);
    } on ApiException catch (e) {
      if (e.statusCode == 400) {
        // A plain message from the server (e.g. no email for the code) is
        // kept; otherwise it was the password.
        final general = e.field('non_field_errors');
        throw ApiException(
          general != null && !general.contains('Unable to log in')
              ? general
              : "That email and password don't match an account.",
          statusCode: 400,
        );
      }
      rethrow;
    }
  }

  /// Exchanges the emailed code for a token; [remember] trusts this phone.
  Future<AuthResult> verify(
    CodeChallenge challenge,
    String code, {
    String? deviceId,
    bool remember = true,
  }) async {
    try {
      return _result(
        await _api.post('/api/auth/login/verify/', {
          'challenge': challenge.id,
          'code': code.replaceAll(RegExp(r'\s'), ''),
          'device_id': ?deviceId,
          'remember_device': remember,
        }),
      );
    } on ApiException catch (e) {
      throw ApiException(
        e.field('code') ?? e.message,
        statusCode: e.statusCode,
      );
    }
  }

  /// Emails a fresh code for the same challenge.
  Future<CodeChallenge> resend(CodeChallenge challenge) async {
    try {
      return CodeChallenge.fromJson(
        await _api.post('/api/auth/login/resend/', {'challenge': challenge.id})
            as Map<String, dynamic>,
      );
    } on ApiException catch (e) {
      throw ApiException(
        e.field('code') ?? e.message,
        statusCode: e.statusCode,
      );
    }
  }

  /// Emails a code for choosing a new password (#126). The server answers
  /// the same way whether or not the email has an account.
  Future<CodeChallenge> requestPasswordReset(String email) async {
    try {
      return CodeChallenge.fromJson(
        await _api.post('/api/auth/password-reset/', {
          'email': _normalize(email),
        }) as Map<String, dynamic>,
      );
    } on ApiException catch (e) {
      throw ApiException(
        e.field('email') ?? e.message,
        statusCode: e.statusCode,
      );
    }
  }

  /// Emails a fresh reset code for the same challenge.
  Future<CodeChallenge> resendPasswordReset(CodeChallenge challenge) async {
    try {
      return CodeChallenge.fromJson(
        await _api.post('/api/auth/password-reset/resend/', {
          'challenge': challenge.id,
        }) as Map<String, dynamic>,
      );
    } on ApiException catch (e) {
      throw ApiException(
        e.field('code') ?? e.message,
        statusCode: e.statusCode,
      );
    }
  }

  /// Sets the new password with the emailed code, and signs in. A problem
  /// with the password comes back as a `new_password` field error; one with
  /// the code, as the message.
  Future<AuthResult> confirmPasswordReset(
    CodeChallenge challenge,
    String code,
    String newPassword, {
    String? deviceId,
    bool remember = true,
  }) async {
    try {
      return _result(
        await _api.post('/api/auth/password-reset/confirm/', {
          'challenge': challenge.id,
          'code': code.replaceAll(RegExp(r'\s'), ''),
          'new_password': newPassword,
          'device_id': ?deviceId,
          'remember_device': remember,
        }),
      );
    } on ApiException catch (e) {
      final password = e.fieldErrors['new_password'];
      throw ApiException(
        e.field('code') ??
            (password == null
                ? e.message
                : 'Please choose a different password.'),
        statusCode: e.statusCode,
        fieldErrors: {'new_password': ?password},
      );
    }
  }

  /// Signs in (or registers) with a Google ID token (#130). No emailed code
  /// is needed; [remember] trusts this phone.
  Future<AuthResult> google(
    String idToken, {
    String? deviceId,
    bool remember = true,
  }) async {
    try {
      return _result(
        await _api.post('/api/auth/google/', {
          'id_token': idToken,
          'device_id': ?deviceId,
          'remember_device': remember,
        }),
      );
    } on ApiException catch (e) {
      throw ApiException(
        e.field('non_field_errors') ?? e.message,
        statusCode: e.statusCode,
      );
    }
  }

  Future<void> logout() => _api.post('/api/auth/logout/');

  /// The current privacy notice (#136).
  Future<PrivacyNotice> privacyNotice() async => PrivacyNotice.fromJson(
    await _api.get('/api/privacy-notice/') as Map<String, dynamic>,
  );

  /// Records agreement to the notice [version]; returns the updated user.
  Future<AppUser> agreeToPrivacy(String version) async => AppUser.fromJson(
    await _api.post('/api/auth/privacy-consent/', {'version': version})
        as Map<String, dynamic>,
  );

  /// Deletes the signed-in account and everything it owns (#134).
  ///
  /// Confirmed with the [password], or with the account's [email] when it
  /// has no password; a 400 names the field that was wrong.
  Future<void> deleteAccount({String? password, String? email}) =>
      _api.delete('/api/auth/me/', {'password': ?password, 'email': ?email});

  /// Changes the password while signed in (#142). The server replaces the
  /// token, signing out other phones, and returns the new one.
  Future<AuthResult> changePassword(String current, String newPassword) async =>
      _result(
        await _api.post('/api/auth/password/', {
          'current_password': current,
          'new_password': newPassword,
        }),
      );

  Future<AppUser> me() async =>
      AppUser.fromJson(await _api.get('/api/auth/me/') as Map<String, dynamic>);

  static String _normalize(String email) => email.trim().toLowerCase();

  static LoginOutcome _outcome(dynamic data) {
    final json = data as Map<String, dynamic>;
    if (json['token'] != null) return SignedIn(_result(json));
    return CodeRequired(CodeChallenge.fromJson(json));
  }

  static AuthResult _result(dynamic data) {
    final json = data as Map<String, dynamic>;
    return AuthResult(
      json['token'] as String,
      AppUser.fromJson(json['user'] as Map<String, dynamic>),
    );
  }
}
