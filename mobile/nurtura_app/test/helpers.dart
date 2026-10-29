import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:nurtura_app/services/google_auth.dart';
import 'package:nurtura_app/main.dart';
import 'package:nurtura_app/services/api_client.dart';
import 'package:nurtura_app/services/biometrics.dart';
import 'package:nurtura_app/state/device_id_store.dart';
import 'package:nurtura_app/state/fingerprint_store.dart';
import 'package:nurtura_app/state/preferences.dart';
import 'package:nurtura_app/state/recommendation_cache.dart';
import 'package:nurtura_app/state/token_store.dart';
import 'package:nurtura_app/theme/app_theme.dart';

/// JSON response the way Django REST Framework sends it (no charset).
http.Response json(Object? body, [int status = 200]) => http.Response.bytes(
  utf8.encode(jsonEncode(body)),
  status,
  headers: {'content-type': 'application/json'},
);

/// Records every request sent to the fake backend.
///
/// Unless [serveChildren] is false, `GET /api/children/` returns [children],
/// so tests that sign in land on the children screen.
class FakeBackend {
  FakeBackend(
    this.handler, {
    this.children = const [],
    this.serveChildren = true,
  });

  final Future<http.Response> Function(http.Request request) handler;
  final List<Map<String, dynamic>> children;
  final bool serveChildren;
  final requests = <http.Request>[];

  late final client = MockClient((request) {
    requests.add(request);
    if (serveChildren &&
        request.method == 'GET' &&
        request.url.path == '/api/children/') {
      return Future.value(json(children));
    }
    return handler(request);
  });

  List<http.Request> to(String path) =>
      requests.where((r) => r.url.path == path).toList();
}

/// Pumps the whole app against a fake backend.
Future<MemoryTokenStore> pumpApp(
  WidgetTester tester,
  FakeBackend backend, {
  String? savedToken,
  RecommendationCache? cache,
  Preferences? preferences,
  DeviceIdStore? deviceIds,
  GoogleIdTokens? google,
  Biometrics biometrics = const NoBiometrics(),
  FingerprintStore? fingerprints,
}) async {
  AppText.useGoogleFonts = false;
  final store = MemoryTokenStore(savedToken);
  await tester.pumpWidget(
    NurturaApp(
      api: ApiClient(baseUrl: 'http://test', httpClient: backend.client),
      tokenStore: store,
      recommendationCache: cache ?? MemoryRecommendationCache(),
      preferences: preferences ?? MemoryPreferences(),
      deviceIds: deviceIds ?? MemoryDeviceIdStore(testDeviceId),
      google: google,
      biometrics: biometrics,
      fingerprints: fingerprints,
    ),
  );
  await tester.pumpAndSettle();
  return store;
}

const testDeviceId = 'test-device-0123456789abcdef';

const caregiverJson = {
  'id': 7,
  'username': 'wanjiru@example.com',
  'email': 'wanjiru@example.com',
  'first_name': '',
  'last_name': '',
  'role': 'caregiver',
};
