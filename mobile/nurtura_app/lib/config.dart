import 'package:flutter/foundation.dart';

const _definedApiBaseUrl = String.fromEnvironment('API_BASE_URL');

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
