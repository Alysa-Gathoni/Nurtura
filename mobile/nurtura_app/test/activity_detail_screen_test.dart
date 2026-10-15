import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';
import 'recommendations_screen_test.dart' as recs;

void main() {
  testWidgets('tapping a card opens its details from the same data', (
    tester,
  ) async {
    final backend = FakeBackend(
      (r) async =>
          json(recs.batch([recs.card('ACT-0004', 'Naming Everyday Objects')])),
    );
    await recs.pumpScreen(tester, backend);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('recommendation_ACT-0004')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('activityDetail')), findsOneWidget);
    expect(find.text('Naming Everyday Objects'), findsOneWidget);
    expect(find.text('Language'), findsOneWidget);
    expect(find.text('12–18 months'), findsOneWidget);
    expect(find.text('How to play'), findsOneWidget);
    expect(find.text('Name things you see together.'), findsOneWidget);
    expect(find.byKey(const Key('explanationBox')), findsOneWidget);
    expect(find.text('Picked for Amani on 11 Oct 2026.'), findsOneWidget);
    // No further request: the detail uses what the list already had.
    expect(backend.requests, hasLength(1));
  });

  testWidgets('no explanation box when the explanation is empty', (
    tester,
  ) async {
    final backend = FakeBackend(
      (r) async => json(
        recs.batch([
          recs.card('ACT-0004', 'Naming Everyday Objects', explanation: ''),
        ]),
      ),
    );
    await recs.pumpScreen(tester, backend);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('recommendation_ACT-0004')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('activityDetail')), findsOneWidget);
    expect(find.byKey(const Key('explanationBox')), findsNothing);
    expect(
      find.textContaining(RegExp('score|rank', caseSensitive: false)),
      findsNothing,
    );
  });
}
