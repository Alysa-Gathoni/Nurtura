import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/state/children_state.dart';
import 'package:nurtura_app/state/preferences.dart';
import 'package:nurtura_app/state/recommendation_cache.dart';

import 'children_screen_test.dart' show childJson, tapVisible;
import 'helpers.dart';
import 'recommendations_screen_test.dart' as recs;

FakeBackend online() => FakeBackend((r) async {
  if (r.url.path == recs.path) {
    return json(recs.batch([recs.card('ACT-0001', 'Tummy Time')]));
  }
  if (r.url.path == '/api/auth/logout/') return http.Response('', 204);
  return json(caregiverJson);
}, children: [childJson()]);

FakeBackend offline() => FakeBackend(
  (r) async => throw http.ClientException('offline'),
  serveChildren: false,
);

/// Opens the app afresh, as after closing it (new providers, same phone).
Future<String?> relaunch(
  WidgetTester tester,
  FakeBackend backend, {
  required String? token,
  required Preferences prefs,
  required RecommendationCache cache,
}) async {
  await tester.pumpWidget(const SizedBox());
  final store = await pumpApp(
    tester,
    backend,
    savedToken: token,
    preferences: prefs,
    cache: cache,
  );
  return store.token;
}

void main() {
  testWidgets('opened offline, the saved session and ideas are still there', (
    tester,
  ) async {
    final prefs = MemoryPreferences();
    final cache = MemoryRecommendationCache();
    await relaunch(tester, online(), token: 'tok', prefs: prefs, cache: cache);
    expect(find.text('Tummy Time'), findsOneWidget);
    expect(prefs.values[ChildrenState.savedKey], contains('Amani'));

    final token = await relaunch(
      tester,
      offline(),
      token: 'tok',
      prefs: prefs,
      cache: cache,
    );
    expect(token, 'tok'); // not signed out
    expect(find.byKey(const Key('emailField')), findsNothing);
    expect(find.text('Tummy Time'), findsOneWidget);
    expect(find.byKey(const Key('savedRecommendationsNotice')), findsOneWidget);

    await tapVisible(tester, find.byKey(const Key('tab_family')));
    expect(find.byKey(const Key('offlineChildrenNotice')), findsOneWidget);
    expect(find.text('Amani'), findsOneWidget);
  });

  testWidgets('offline with nothing saved: still signed in, with a retry', (
    tester,
  ) async {
    final token = await relaunch(
      tester,
      offline(),
      token: 'tok',
      prefs: MemoryPreferences(),
      cache: MemoryRecommendationCache(),
    );
    expect(token, 'tok');
    expect(find.byKey(const Key('emailField')), findsNothing);
    expect(find.byKey(const Key('retryButton')), findsOneWidget);
  });

  testWidgets('an ended session (401) still signs out and forgets the list', (
    tester,
  ) async {
    final prefs = MemoryPreferences({
      ChildrenState.savedKey:
          '[{"id":3,"name":"Amani",'
          '"date_of_birth":"2025-08-01","interests":[],"concerns":[]}]',
    });
    final token = await relaunch(
      tester,
      FakeBackend((r) async => json({'detail': 'Invalid token.'}, 401)),
      token: 'expired',
      prefs: prefs,
      cache: MemoryRecommendationCache(),
    );
    expect(token, isNull);
    expect(find.byKey(const Key('emailField')), findsOneWidget);
    expect(prefs.values.containsKey(ChildrenState.savedKey), isFalse);
  });

  testWidgets('logging out forgets the saved list', (tester) async {
    final prefs = MemoryPreferences();
    await relaunch(
      tester,
      online(),
      token: 'tok',
      prefs: prefs,
      cache: MemoryRecommendationCache(),
    );
    expect(prefs.values.containsKey(ChildrenState.savedKey), isTrue);
    await tapVisible(tester, find.byKey(const Key('tab_family')));
    await tapVisible(tester, find.byKey(const Key('logoutButton')));
    expect(find.byKey(const Key('emailField')), findsOneWidget);
    expect(prefs.values.containsKey(ChildrenState.savedKey), isFalse);
  });
}
