import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/models/recommendation.dart';
import 'package:nurtura_app/state/recommendation_cache.dart';
import 'package:nurtura_app/state/token_store.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers.dart';
import 'recommendations_screen_test.dart' as recs;

void main() {
  testWidgets('a batch from the server is saved on the device', (tester) async {
    final cache = MemoryRecommendationCache();
    final backend = FakeBackend(
      (r) async => json(recs.batch([recs.card('ACT-0001', 'Tummy Time')])),
    );
    await recs.pumpScreen(tester, backend, cache: cache);
    await tester.pumpAndSettle();

    final saved = await cache.read(3);
    expect(saved!.batch.items.single.activityName, 'Tummy Time');
    expect(find.byKey(const Key('savedRecommendationsNotice')), findsNothing);
  });

  testWidgets('offline, the saved batch is shown with a notice', (
    tester,
  ) async {
    final cache = MemoryRecommendationCache();
    await cache.write(
      3,
      RecommendationBatch.fromJson(
        recs.batch([recs.card('ACT-0001', 'Tummy Time')]),
      ),
    );
    final backend = FakeBackend(
      (r) async => throw http.ClientException('offline'),
    );
    await recs.pumpScreen(tester, backend, cache: cache);
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('savedRecommendationsNotice')), findsOneWidget);
    expect(find.textContaining('Saved ideas from'), findsOneWidget);
    expect(find.text('Tummy Time'), findsOneWidget);
    expect(find.byKey(const Key('explanationBox')), findsOneWidget);
    expect(find.byKey(const Key('recommendationsError')), findsNothing);
  });

  testWidgets('offline with nothing saved shows the error and a retry', (
    tester,
  ) async {
    final backend = FakeBackend(
      (r) async => throw http.ClientException('offline'),
    );
    await recs.pumpScreen(tester, backend, cache: MemoryRecommendationCache());
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('recommendationsError')), findsOneWidget);
    expect(find.byKey(const Key('retryButton')), findsOneWidget);
  });

  testWidgets('a server answer (404) never falls back to the saved batch', (
    tester,
  ) async {
    final cache = MemoryRecommendationCache();
    await cache.write(
      3,
      RecommendationBatch.fromJson(
        recs.batch([recs.card('ACT-0001', 'Tummy Time')]),
      ),
    );
    final backend = FakeBackend((r) async => json({'detail': 'x'}, 404));
    await recs.pumpScreen(tester, backend, cache: cache);
    await tester.pumpAndSettle();
    expect(find.text('Tummy Time'), findsNothing);
    expect(find.byKey(const Key('recommendationsError')), findsOneWidget);
  });

  testWidgets('a 401 clears what was saved', (tester) async {
    final cache = MemoryRecommendationCache();
    await cache.write(
      3,
      RecommendationBatch.fromJson(
        recs.batch([recs.card('ACT-0001', 'Tummy Time')]),
      ),
    );
    final store = MemoryTokenStore('tok');
    final backend = FakeBackend((r) async => json({'detail': 'x'}, 401));
    await recs.pumpScreen(tester, backend, cache: cache, store: store);
    // The standalone screen is the first route, so nothing is popped and its
    // spinner keeps going: pump for a while instead of settling.
    await tester.pump(const Duration(milliseconds: 500));
    expect(cache.entries, isEmpty);
    expect(await store.read(), isNull);
  });

  testWidgets('logging out clears what was saved', (tester) async {
    final cache = MemoryRecommendationCache();
    await cache.write(
      3,
      RecommendationBatch.fromJson(
        recs.batch([recs.card('ACT-0001', 'Tummy Time')]),
      ),
    );
    final backend = FakeBackend((r) async => json(caregiverJson));
    await pumpApp(tester, backend, savedToken: 'tok', cache: cache);
    await tester.tap(find.byKey(const Key('logoutButton')));
    await tester.pumpAndSettle();
    expect(cache.entries, isEmpty);
  });

  test(
    'the device cache round-trips a batch and clears only its own keys',
    () async {
      SharedPreferences.setMockInitialValues({'other.setting': 'keep'});
      final cache = SharedPrefsRecommendationCache();
      final batch = RecommendationBatch.fromJson(
        recs.batch([
          recs.card('ACT-0001', 'Tummy Time'),
          recs.card('ACT-0002', 'Singing', position: 2, explanation: ''),
        ]),
      );
      await cache.write(3, batch);
      final read = await cache.read(3);
      expect(read!.batch.toJson(), batch.toJson());
      expect(await cache.read(4), isNull);

      await cache.clear();
      expect(await cache.read(3), isNull);
      final prefs = await SharedPreferences.getInstance();
      expect(prefs.getString('other.setting'), 'keep');
    },
  );
}
