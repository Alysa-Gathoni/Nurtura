import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/models/child_profile.dart';
import 'package:nurtura_app/screens/recommendations_screen.dart';
import 'package:nurtura_app/services/api_client.dart';
import 'package:nurtura_app/services/recommendation_service.dart';
import 'package:nurtura_app/state/auth_state.dart';
import 'package:nurtura_app/state/token_store.dart';
import 'package:nurtura_app/theme/app_theme.dart';
import 'package:provider/provider.dart';

import 'helpers.dart';

const path = '/api/children/3/recommendations/';

Map<String, dynamic> card(
  String id,
  String name, {
  int position = 1,
  String explanation = 'You recorded “Waves ‘bye-bye’” as not yet.',
}) => {
  'id': position,
  'batch': 'b-1',
  'position': position,
  'generated_at': '2026-10-11T09:00:00Z',
  'activity_id': id,
  'activity_name': name,
  'developmental_domain': 'Language',
  'age_range': '12-18 months',
  'short_description': 'Name things you see together.',
  'explanation': explanation,
};

Map<String, dynamic> batch(List<Map<String, dynamic>> cards) => {
  'batch': cards.isEmpty ? null : 'b-1',
  'generated_at': cards.isEmpty ? null : '2026-10-11T09:00:00Z',
  'recommendations': cards,
};

final emptyBatch = batch(const []);

final child = ChildProfile(
  id: 3,
  name: 'Amani',
  dateOfBirth: DateTime(2025, 6, 1),
);

/// The recommendations screen on its own, against a fake backend.
Future<void> pumpScreen(
  WidgetTester tester,
  FakeBackend backend, {
  bool refresh = false,
}) async {
  AppText.useGoogleFonts = false;
  final api = ApiClient(baseUrl: 'http://test', httpClient: backend.client)
    ..token = 'tok';
  await tester.pumpWidget(
    MultiProvider(
      providers: [
        Provider.value(value: api),
        ChangeNotifierProvider(
          create: (_) => AuthState(api: api, store: MemoryTokenStore('tok')),
        ),
      ],
      child: MaterialApp(
        home: RecommendationsScreen(child: child, refresh: refresh),
      ),
    ),
  );
}

void main() {
  testWidgets('shows the newest batch without generating one', (tester) async {
    final backend = FakeBackend(
      (r) async => json(
        batch([
          card('ACT-0004', 'Naming Everyday Objects'),
          card('ACT-0031', 'Naming Pictures in a Book', position: 2),
        ]),
      ),
    );
    await pumpScreen(tester, backend);
    await tester.pumpAndSettle();

    expect(find.text('Naming Everyday Objects'), findsOneWidget);
    expect(find.text('Naming Pictures in a Book'), findsOneWidget);
    expect(find.text('Language'), findsNWidgets(2));
    expect(find.text('12–18 months'), findsNWidgets(2));
    expect(find.text('Name things you see together.'), findsNWidgets(2));
    expect(find.byKey(const Key('explanationBox')), findsNWidgets(2));
    expect(backend.to(path).map((r) => r.method), ['GET']);
    // No rank numbers or scores anywhere.
    expect(find.text('1'), findsNothing);
    expect(find.text('2'), findsNothing);
    expect(
      find.textContaining(RegExp(r'score|rank', caseSensitive: false)),
      findsNothing,
    );
  });

  testWidgets('hides the explanation box when the explanation is empty', (
    tester,
  ) async {
    final backend = FakeBackend(
      (r) async => json(
        batch([
          card('ACT-0004', 'Naming Everyday Objects'),
          card(
            'ACT-0031',
            'Naming Pictures in a Book',
            position: 2,
            explanation: '',
          ),
        ]),
      ),
    );
    await pumpScreen(tester, backend);
    await tester.pumpAndSettle();

    final withExplanation = find.byKey(const Key('recommendation_ACT-0004'));
    final without = find.byKey(const Key('recommendation_ACT-0031'));
    expect(
      find.descendant(
        of: withExplanation,
        matching: find.byKey(const Key('explanationBox')),
      ),
      findsOneWidget,
    );
    expect(
      find.descendant(
        of: without,
        matching: find.byKey(const Key('explanationBox')),
      ),
      findsNothing,
    );
    expect(find.text('Why this?'), findsOneWidget);
  });

  for (final status in [200, 201]) {
    testWidgets('generates when there is no batch yet (POST $status)', (
      tester,
    ) async {
      final backend = FakeBackend((r) async {
        if (r.method == 'GET') return json(emptyBatch);
        return json(
          batch([card('ACT-0023', 'Animal Sound Imitation Game')]),
          status,
        );
      });
      await pumpScreen(tester, backend);
      await tester.pumpAndSettle();

      expect(backend.to(path).map((r) => r.method), ['GET', 'POST']);
      expect(find.text('Animal Sound Imitation Game'), findsOneWidget);
      expect(find.byKey(const Key('explanationBox')), findsOneWidget);
      expect(find.byKey(const Key('recommendationsError')), findsNothing);
    });
  }

  testWidgets('shows "Preparing recommendations..." while generating', (
    tester,
  ) async {
    final post = Completer<http.Response>();
    final backend = FakeBackend((r) async {
      if (r.method == 'GET') return json(emptyBatch);
      return post.future;
    });
    await pumpScreen(tester, backend);
    await tester.pump(); // GET answered
    await tester.pump();

    expect(find.byKey(const Key('preparingRecommendations')), findsOneWidget);
    expect(find.text('Preparing recommendations...'), findsOneWidget);
    expect(
      find.text('This can take up to half a minute the first time.'),
      findsOneWidget,
    );

    post.complete(json(batch([card('ACT-0001', 'Tummy Time')]), 201));
    await tester.pumpAndSettle();
    expect(find.text('Preparing recommendations...'), findsNothing);
    expect(find.text('Tummy Time'), findsOneWidget);
  });

  testWidgets('allows at least 30 seconds for generating', (tester) async {
    expect(
      RecommendationService.generateTimeout,
      greaterThanOrEqualTo(const Duration(seconds: 30)),
    );
  });

  testWidgets('a network error can be retried', (tester) async {
    var calls = 0;
    final backend = FakeBackend((r) async {
      calls++;
      if (calls == 1) throw http.ClientException('offline');
      return json(batch([card('ACT-0001', 'Tummy Time')]));
    });
    await pumpScreen(tester, backend);
    await tester.pumpAndSettle();

    expect(
      find.textContaining("Can't reach the Nurtura server"),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const Key('retryButton')));
    await tester.pumpAndSettle();
    expect(find.text('Tummy Time'), findsOneWidget);
  });

  testWidgets('403 and 404 get plain messages', (tester) async {
    for (final (status, message) in [
      (403, 'Recommendations are only available on caregiver accounts.'),
      (404, "We couldn't find Amani's profile. It may have been removed."),
    ]) {
      final backend = FakeBackend((r) async => json({'detail': 'x'}, status));
      await pumpScreen(tester, backend);
      await tester.pumpAndSettle();
      expect(find.text(message), findsOneWidget, reason: 'status $status');
      await tester.pumpWidget(const SizedBox());
    }
  });

  testWidgets('no activities to suggest', (tester) async {
    final backend = FakeBackend((r) async => json(emptyBatch));
    await pumpScreen(tester, backend);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('noRecommendations')), findsOneWidget);
  });

  testWidgets('refresh asks for a fresh batch', (tester) async {
    final backend = FakeBackend(
      (r) async => json(
        batch([card('ACT-0001', 'Tummy Time')]),
        r.method == 'POST' ? 201 : 200,
      ),
    );
    await pumpScreen(tester, backend);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('refreshRecommendationsButton')));
    await tester.pumpAndSettle();
    expect(backend.to(path).map((r) => r.method), ['GET', 'POST']);
  });

  testWidgets('opened right after recording a milestone, it regenerates', (
    tester,
  ) async {
    final backend = FakeBackend(
      (r) async => json(batch([card('ACT-0001', 'Tummy Time')]), 201),
    );
    await pumpScreen(tester, backend, refresh: true);
    await tester.pumpAndSettle();
    expect(backend.to(path).map((r) => r.method), ['POST']);
  });

  testWidgets('401 returns to the login screen', (tester) async {
    final backend = FakeBackend(
      (r) async {
        if (r.url.path == '/api/auth/me/') return json(caregiverJson);
        if (r.url.path == path) return json({'detail': 'Invalid token.'}, 401);
        return json([]);
      },
      children: [
        {
          'id': 3,
          'name': 'Amani',
          'date_of_birth': '2025-06-01',
          'interests': [],
          'concerns': [],
        },
      ],
    );
    final store = await pumpApp(tester, backend, savedToken: 'tok');
    await tester.tap(find.byKey(const Key('child_3')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('openRecommendationsButton')));
    await tester.pumpAndSettle();

    expect(find.text('Log in'), findsWidgets);
    expect(await store.read(), isNull);
  });
}
