import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:nurtura_app/main.dart';
import 'package:nurtura_app/services/api_client.dart';
import 'package:nurtura_app/state/token_store.dart';
import 'package:nurtura_app/theme/app_theme.dart';

/// JSON response the way Django REST Framework sends it (no charset).
http.Response json(Object? body, [int status = 200]) => http.Response.bytes(
      utf8.encode(jsonEncode(body)),
      status,
      headers: {'content-type': 'application/json'},
    );

/// Records every request sent to the fake backend.
class FakeBackend {
  FakeBackend(this.handler);

  final Future<http.Response> Function(http.Request request) handler;
  final requests = <http.Request>[];

  late final client = MockClient((request) {
    requests.add(request);
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
}) async {
  AppText.useGoogleFonts = false;
  final store = MemoryTokenStore(savedToken);
  await tester.pumpWidget(
    NurturaApp(
      api: ApiClient(baseUrl: 'http://test', httpClient: backend.client),
      tokenStore: store,
    ),
  );
  await tester.pumpAndSettle();
  return store;
}

const caregiverJson = {
  'id': 7,
  'username': 'wanjiru@example.com',
  'email': 'wanjiru@example.com',
  'first_name': '',
  'last_name': '',
  'role': 'caregiver',
};
