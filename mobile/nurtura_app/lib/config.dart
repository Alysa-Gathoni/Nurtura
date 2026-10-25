import 'package:flutter/foundation.dart';

const _definedApiBaseUrl = String.fromEnvironment('API_BASE_URL');

/// The *web* OAuth client ID for "Continue with Google" (#130), the same one
/// the backend has in GOOGLE_OAUTH_CLIENT_IDS. Set it with
/// `--dart-define=GOOGLE_SERVER_CLIENT_ID=...`; without it, the button is
/// hidden. Android only for now.
const googleServerClientId = String.fromEnvironment('GOOGLE_SERVER_CLIENT_ID');

bool get googleSignInConfigured =>
    googleServerClientId.isNotEmpty &&
    !kIsWeb &&
    defaultTargetPlatform == TargetPlatform.android;

/// Base URL of the Django backend.
///
/// Override with `--dart-define=API_BASE_URL=https://...`. Defaults to the
/// local dev server; the Android emulator reaches the host machine at
/// 10.0.2.2 rather than 127.0.0.1.
String get apiBaseUrl {
  if (_definedApiBaseUrl.isNotEmpty) return _definedApiBaseUrl;
  if (!kIsWeb && defaultTargetPlatform == TargetPlatform.android) {
    return 'http://10.0.2.2:8000';
  }
  return 'http://127.0.0.1:8000';
}
