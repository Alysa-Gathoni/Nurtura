import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';

import 'api_client.dart';

/// Gets a Google ID token for "Continue with Google" (#130). Behind an
/// interface so tests can stand in for Google.
abstract class GoogleIdTokens {
  /// The ID token for the account the person picks, or null if they
  /// closed the chooser.
  Future<String?> idToken();

  /// Forgets the chosen account, so the chooser shows next time.
  Future<void> signOut();
}

/// Google Sign-In on Android (Credential Manager).
///
/// [serverClientId] is the *web* OAuth client ID the backend checks tokens
/// against. The Android client ID isn't passed: Google matches it by the
/// app ID and the signing key's SHA-1, registered in Google Cloud Console.
class GooglePlayIdTokens implements GoogleIdTokens {
  GooglePlayIdTokens(this.serverClientId);

  final String serverClientId;
  Future<void>? _ready;

  Future<void> _init() => _ready ??= GoogleSignIn.instance.initialize(
    serverClientId: serverClientId,
  );

  @override
  Future<String?> idToken() async {
    try {
      await _init();
      final account = await GoogleSignIn.instance.authenticate();
      return account.authentication.idToken;
    } on GoogleSignInException catch (e) {
      if (e.code == GoogleSignInExceptionCode.canceled ||
          e.code == GoogleSignInExceptionCode.interrupted) {
        return null;
      }
      debugPrint('Google sign-in failed: ${e.code} ${e.description}');
      throw ApiException(
        e.code == GoogleSignInExceptionCode.clientConfigurationError ||
                e.code == GoogleSignInExceptionCode.providerConfigurationError
            ? "Google sign-in isn't set up for this version of the app yet. "
                  'Please use your email.'
            : "Google sign-in didn't work. Please try again, or use your email.",
      );
    }
  }

  @override
  Future<void> signOut() async {
    try {
      await _init();
      await GoogleSignIn.instance.signOut();
    } on Exception {
      // Nothing to forget, or Google is unreachable: either way, fine.
    }
  }
}
