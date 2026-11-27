import 'dart:async';
import 'dart:convert' show jsonDecode, jsonEncode;

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/models/child_profile.dart';
import 'package:nurtura_app/models/recommendation.dart';
import 'package:nurtura_app/screens/recommendations_screen.dart';
import 'package:nurtura_app/services/api_client.dart';
import 'package:nurtura_app/services/recommendation_service.dart';
import 'package:nurtura_app/state/auth_state.dart';
import 'package:nurtura_app/state/device_id_store.dart';
import 'package:nurtura_app/state/engagement.dart';
import 'package:nurtura_app/state/preferences.dart';
import 'package:nurtura_app/state/recommendation_cache.dart';
import 'package:nurtura_app/state/token_store.dart';
import 'package:nurtura_app/theme/app_theme.dart';
import 'package:nurtura_app/utils/dates.dart';
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
  RecommendationCache? cache,
  MemoryTokenStore? store,
  EngagementState? engagement,
  ChildProfile? forChild,
}) async {
  AppText.useGoogleFonts = false;
  final api = ApiClient(baseUrl: 'http://test', httpClient: backend.client)
    ..token = 'tok';
  await tester.pumpWidget(
    MultiProvider(
      providers: [
        Provider.value(value: api),
        Provider<RecommendationCache>.value(
          value: cache ?? MemoryRecommendationCache(),
        ),
        ChangeNotifierProvider(
          create: (_) => engagement ?? EngagementState(MemoryPreferences()),
        ),
        ChangeNotifierProvider(
          create: (_) => AuthState(
            api: api,
            store: store ?? MemoryTokenStore('tok'),
            deviceIds: MemoryDeviceIdStore(),
            onSessionCleared: (cache ?? MemoryRecommendationCache()).clear,
          ),
        ),
      ],
      child: MaterialApp(
        home: RecommendationsScreen(child: forChild ?? child, refresh: refresh),
      ),
    ),
  );
}

void main() {
  testWidgets('pregnancy ideas say what to do, not how to play (#291)', (
    tester,
  ) async {
    final prenatal = card('ACT-0002', 'Talking and Singing to the Baby');
    final backend = FakeBackend((r) async => json(batch([prenatal])));
    final due = DateTime.now().add(const Duration(days: 60));
    await pumpScreen(
      tester,
      backend,
      forChild: ChildProfile(id: 4, name: 'Zawadi', dateOfBirth: due),
    );
    await tester.pumpAndSettle();
    expect(find.text('Tap an idea to see what to do.'), findsOneWidget);
    expect(find.text('Tap an idea to see how to play.'), findsNothing);
  });

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
    expect(find.text('Talking'), findsNWidgets(2));
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

  group('weekly plan (#244)', () {
    // Plans are built around today (#285): the app compares a plan's last
    // day with the real date, so fixed dates fail once they have passed.
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    DateTime day(int offset) =>
        DateTime(today.year, today.month, today.day + offset);
    String iso(DateTime d) => d.toIso8601String().substring(0, 10);

    // This week: started yesterday, ends in five days.
    final starts = day(-1);
    final ends = day(5);

    Map<String, dynamic> weekBatch({required bool ended}) => {
      ...batch([
        {
          ...card('ACT-0004', 'Naming Everyday Objects'),
          'completion': {'status': 'completed', 'completion_date': iso(today)},
        },
        card('ACT-0031', 'Naming Pictures in a Book', position: 2),
      ]),
      'plan': {'starts': iso(starts), 'ends': iso(ends), 'ended': ended},
    };

    testWidgets('shows the week, how many were tried and when new ideas come', (
      tester,
    ) async {
      final backend = FakeBackend((r) async => json(weekBatch(ended: false)));
      await pumpScreen(tester, backend);
      await tester.pumpAndSettle();

      expect(backend.to(path).map((r) => r.method), ['GET']);
      expect(
        find.text('This week: ${formatWeek(starts, ends)}'),
        findsOneWidget,
      );
      expect(
        find.text('1 of 2 tried · New ideas on ${formatShortDate(day(6))}'),
        findsOneWidget,
      );
    });

    testWidgets('a plan whose week has ended is replaced by a new one', (
      tester,
    ) async {
      final backend = FakeBackend((r) async {
        if (r.method == 'GET') return json(weekBatch(ended: true));
        return json({
          ...batch([card('ACT-0023', 'Animal Sound Imitation Game')]),
          'plan': {'starts': iso(today), 'ends': iso(day(6)), 'ended': false},
        }, 201);
      });
      await pumpScreen(tester, backend);
      await tester.pumpAndSettle();

      expect(backend.to(path).map((r) => r.method), ['GET', 'POST']);
      expect(find.text('Animal Sound Imitation Game'), findsOneWidget);
      expect(
        find.text('This week: ${formatWeek(today, day(6))}'),
        findsOneWidget,
      );
      expect(
        find.text('0 of 1 tried · New ideas on ${formatShortDate(day(7))}'),
        findsOneWidget,
      );
    });

    test('a saved plan counts as ended once its last day has passed', () {
      final plan = WeekPlan(
        starts: DateTime(2026, 11, 19),
        ends: DateTime(2026, 11, 25),
      );
      expect(plan.endedOn(DateTime(2026, 11, 25, 23, 59)), isFalse);
      expect(plan.endedOn(DateTime(2026, 11, 26)), isTrue);
    });
  });

  testWidgets('shows "Gathering ideas…" while generating', (tester) async {
    final post = Completer<http.Response>();
    final backend = FakeBackend((r) async {
      if (r.method == 'GET') return json(emptyBatch);
      return post.future;
    });
    await pumpScreen(tester, backend);
    await tester.pump(); // GET answered
    await tester.pump();

    expect(find.byKey(const Key('preparingRecommendations')), findsOneWidget);
    expect(find.text('Gathering ideas…'), findsOneWidget);
    expect(
      find.text('The first time can take up to 30 seconds.'),
      findsOneWidget,
    );

    post.complete(json(batch([card('ACT-0001', 'Tummy Time')]), 201));
    await tester.pumpAndSettle();
    expect(find.text('Gathering ideas…'), findsNothing);
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

  group('clinic-visit referral (#161)', () {
    final referral = {
      'message':
          'You\'ve marked something as “Not yet” that most children do by '
          'Amani\'s age.',
      'source': 'CDC Learn the Signs. Act Early. (2022)',
      'milestones': [
        {
          'description': 'Waves “bye-bye”',
          'domain': 'Language',
          'expected_age_months': 12.0,
          'source': 'CDC',
        },
      ],
    };

    testWidgets('shown above the ideas, with its milestones', (tester) async {
      final backend = FakeBackend(
        (r) async => json({
          ...batch([card('ACT-0004', 'Naming Everyday Objects')]),
          'referral': referral,
        }),
      );
      await pumpScreen(tester, backend);
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('referralNotice')), findsOneWidget);
      expect(
        find.text('Worth mentioning at your next clinic visit'),
        findsOneWidget,
      );
      expect(find.textContaining('most children do by'), findsOneWidget);
      expect(find.text('•  Waves “bye-bye”'), findsOneWidget);
      expect(find.text('Naming Everyday Objects'), findsOneWidget);
    });

    testWidgets('shown even when there are no ideas', (tester) async {
      final backend = FakeBackend(
        (r) async => json({...emptyBatch, 'referral': referral}),
      );
      await pumpScreen(tester, backend);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('referralNotice')), findsOneWidget);
      expect(find.byKey(const Key('noRecommendations')), findsOneWidget);
    });

    testWidgets('absent when the server sends null', (tester) async {
      final backend = FakeBackend(
        (r) async => json({
          ...batch([card('ACT-0004', 'Naming Everyday Objects')]),
          'referral': null,
        }),
      );
      await pumpScreen(tester, backend);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('referralNotice')), findsNothing);
    });

    test('kept in the offline copy, and survives an update', () {
      final parsed = RecommendationBatch.fromJson({
        ...batch([card('ACT-0004', 'Naming Everyday Objects')]),
        'referral': referral,
      });
      final again = RecommendationBatch.fromJson(
        jsonDecode(jsonEncode(parsed.toJson())) as Map<String, dynamic>,
      );
      expect(again.referral!.milestones, ['Waves “bye-bye”']);
      expect(again.referral!.message, parsed.referral!.message);
      expect(
        parsed.replacing(parsed.items.first).referral!.message,
        parsed.referral!.message,
      );
      // A copy saved before #161 has no referral and still loads.
      expect(RecommendationBatch.fromJson(batch(const [])).referral, isNull);
    });
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
    // Signed in with a child, the app opens on Today, whose request gets
    // the 401.
    final store = await pumpApp(tester, backend, savedToken: 'tok');

    expect(find.text('Log in'), findsWidgets);
    expect(await store.read(), isNull);
  });
}
