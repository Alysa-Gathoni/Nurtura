import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/utils/dates.dart' as dates;

import 'helpers.dart';

const catalogue = [
  {
    'id': 1,
    'milestone_key': 'CDC-12M-LA-01',
    'domain': 'Language',
    'description': 'Waves "bye-bye"',
    'expected_age_months': 12.0,
    'source': 'CDC',
  },
  {
    'id': 2,
    'milestone_key': 'CDC-36M-LA-05',
    'domain': 'Language',
    'description': 'Talks well enough for others to understand',
    'expected_age_months': 36.0,
    'source': 'CDC',
  },
  {
    'id': 3,
    'milestone_key': 'CDC-09M-MO-04',
    'domain': 'Motor',
    'description': 'Sits without support',
    'expected_age_months': 9.0,
    'source': 'CDC',
  },
  {
    'id': 4,
    'milestone_key': 'WHO-MO-06',
    'domain': 'Motor',
    'description': 'Walking alone',
    'expected_age_months': 17.6,
    'source': 'WHO',
  },
];

/// Filters [catalogue] the way the API does: every search word, and domain.
List<Map<String, dynamic>> searchCatalogue(Uri url) {
  final words = (url.queryParameters['search'] ?? '')
      .toLowerCase()
      .split(' ')
      .where((w) => w.isNotEmpty);
  final domain = url.queryParameters['domain'];
  return [
    for (final m in catalogue)
      if ((domain == null || m['domain'] == domain) &&
          words.every(
            (w) => (m['description'] as String).toLowerCase().contains(w),
          ))
        m,
  ];
}

final child = {
  'id': 3,
  'name': 'Amani',
  'date_of_birth': '2025-09-01', // 13 months old on the fixed clock
  'gender': 'unspecified',
  'interests': [],
  'preferences': {},
  'concerns': [],
  'created_at': '2026-10-01T08:00:00Z',
  'updated_at': '2026-10-01T08:00:00Z',
};

Map<String, dynamic> recordedResponse(String status) => {
  'milestone': {
    'id': 10,
    'reference': 1,
    'reference_key': 'CDC-12M-LA-01',
    'domain': 'Language',
    'description': 'Waves "bye-bye"',
    'status': status,
    'observation_date': '2026-10-01',
    'created_at': '2026-10-01T09:00:00Z',
  },
  'profile': {
    'age_months': 13.0,
    'scores': {'Language': 1.0},
    'ranked_domains': ['Language'],
    'reasons': [],
    'generated_at': '2026-10-01T09:00:00Z',
  },
};

Future<FakeBackend> openMilestoneScreen(
  WidgetTester tester, {
  Future<http.Response> Function(http.Request)? onRecord,
  Future<http.Response> Function(http.Request)? onSearch,
}) async {
  // A tall phone-sized screen, so every result in the short test catalogue
  // is built by the lazy list.
  tester.view.physicalSize = const Size(420, 1400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  final backend = FakeBackend((request) async {
    if (request.url.path == '/api/reference-milestones/') {
      return onSearch?.call(request) ??
          Future.value(json(searchCatalogue(request.url)));
    }
    if (request.url.path == '/api/children/3/milestones/') {
      return onRecord?.call(request) ??
          Future.value(json(recordedResponse('not_yet'), 201));
    }
    if (request.url.path == '/api/children/3/recommendations/') {
      return json({
        'batch': 'b-1',
        'generated_at': '2026-10-01T09:00:00Z',
        'recommendations': [
          {
            'id': 1,
            'batch': 'b-1',
            'position': 1,
            'generated_at': '2026-10-01T09:00:00Z',
            'activity_id': 'ACT-0004',
            'activity_name': 'Naming Everyday Objects',
            'developmental_domain': 'Language',
            'age_range': '12-18 months',
            'short_description': 'Name things you see together.',
            'explanation': 'You recorded “Waves ‘bye-bye’” as not yet.',
          },
        ],
      }, request.method == 'POST' ? 201 : 200);
    }
    return json(caregiverJson);
  }, children: [child]);
  await pumpApp(tester, backend, savedToken: 'tok');
  await tester.tap(find.byKey(const Key('child_3')));
  await tester.pumpAndSettle();
  return backend;
}

List<String> visibleMilestoneKeys(WidgetTester tester) {
  final tiles = find.byWidgetPredicate(
    (w) =>
        w.key is ValueKey<String> &&
        (w.key! as ValueKey<String>).value.startsWith('milestone_'),
  );
  final widgets = tiles.evaluate().map((e) => e.widget).toList()
    ..sort(
      (a, b) => tester
          .getTopLeft(find.byKey(a.key!))
          .dy
          .compareTo(tester.getTopLeft(find.byKey(b.key!)).dy),
    );
  return [
    for (final w in widgets)
      (w.key! as ValueKey<String>).value.substring('milestone_'.length),
  ];
}

Future<void> tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(() => WidgetController.hitTestWarningShouldBeFatal = true);
  setUp(() => dates.clock = () => DateTime(2026, 10, 1, 9));
  tearDown(() => dates.clock = DateTime.now);

  testWidgets('lists catalogue milestones closest to the child\'s age first', (
    tester,
  ) async {
    await openMilestoneScreen(tester);
    expect(find.text('Amani · 13 months'), findsOneWidget);
    expect(visibleMilestoneKeys(tester), [
      'CDC-12M-LA-01', // 1 month away
      'CDC-09M-MO-04', // 4
      'WHO-MO-06', // 4.6
      'CDC-36M-LA-05', // 23
    ]);
    expect(find.text('By 17.6 months · WHO'), findsOneWidget);
  });

  testWidgets('searches as you type, after a short pause', (tester) async {
    final backend = await openMilestoneScreen(tester);
    final before = backend.to('/api/reference-milestones/').length;

    await tester.enterText(
      find.byKey(const Key('milestoneSearchField')).last,
      'waves bye',
    );
    await tester.pump(const Duration(milliseconds: 100));
    expect(backend.to('/api/reference-milestones/'), hasLength(before));

    await tester.pump(const Duration(milliseconds: 300));
    await tester.pumpAndSettle();
    final last = backend.to('/api/reference-milestones/').last;
    expect(last.url.queryParameters['search'], 'waves bye');
    expect(visibleMilestoneKeys(tester), ['CDC-12M-LA-01']);
  });

  testWidgets('filters by domain; there is no Sensory filter', (tester) async {
    final backend = await openMilestoneScreen(tester);
    expect(find.byKey(const Key('domain_Sensory')), findsNothing);

    await tapVisible(tester, find.byKey(const Key('domain_Motor')));
    expect(
      backend
          .to('/api/reference-milestones/')
          .last
          .url
          .queryParameters['domain'],
      'Motor',
    );
    expect(visibleMilestoneKeys(tester), ['CDC-09M-MO-04', 'WHO-MO-06']);

    await tapVisible(tester, find.byKey(const Key('domain_All')));
    expect(
      backend.to('/api/reference-milestones/').last.url.queryParameters,
      isNot(contains('domain')),
    );
  });

  testWidgets('records a Not yet milestone and confirms the profile update', (
    tester,
  ) async {
    final backend = await openMilestoneScreen(tester);

    await tapVisible(tester, find.byKey(const Key('milestone_CDC-12M-LA-01')));
    expect(find.text('How is Amani doing with this?'), findsOneWidget);

    // Saving needs a status first.
    await tapVisible(tester, find.byKey(const Key('saveMilestoneButton')));
    expect(backend.to('/api/children/3/milestones/'), isEmpty);

    await tapVisible(tester, find.byKey(const Key('status_not_yet')));
    await tapVisible(tester, find.byKey(const Key('saveMilestoneButton')));

    final sent = backend.to('/api/children/3/milestones/').single;
    expect(sent.method, 'POST');
    expect(jsonDecode(sent.body), {'reference': 1, 'status': 'not_yet'});
    expect(find.byKey(const Key('milestoneRecorded')), findsOneWidget);
    expect(find.text('“Waves "bye-bye"” — Not yet'), findsOneWidget);
    expect(
      find.text("Amani's developmental profile was updated."),
      findsOneWidget,
    );

    await tapVisible(tester, find.byKey(const Key('recordAnotherButton')));
    expect(find.byKey(const Key('milestoneSearchField')), findsOneWidget);
    expect(find.text('How is Amani doing with this?'), findsNothing);
  });

  testWidgets('after recording, "See ideas" asks for fresh recommendations', (
    tester,
  ) async {
    final backend = await openMilestoneScreen(tester);
    await tapVisible(tester, find.byKey(const Key('milestone_CDC-12M-LA-01')));
    await tapVisible(tester, find.byKey(const Key('status_not_yet')));
    await tapVisible(tester, find.byKey(const Key('saveMilestoneButton')));
    await tapVisible(tester, find.byKey(const Key('seeRecommendationsButton')));

    expect(
      backend.to('/api/children/3/recommendations/').map((r) => r.method),
      ['POST'],
    );
    expect(find.text('Ideas for Amani'), findsOneWidget);
    expect(find.text('Naming Everyday Objects'), findsOneWidget);
  });

  testWidgets('the app bar opens the recommendations', (tester) async {
    final backend = await openMilestoneScreen(tester);
    await tester.tap(find.byKey(const Key('openRecommendationsButton')));
    await tester.pumpAndSettle();
    expect(
      backend.to('/api/children/3/recommendations/').map((r) => r.method),
      ['GET'],
    );
    expect(find.text('Naming Everyday Objects'), findsOneWidget);
  });

  testWidgets('shows why a milestone could not be recorded', (tester) async {
    await openMilestoneScreen(
      tester,
      onRecord: (_) async => json({
        'observation_date': ["Can't be before the date of birth."],
      }, 400),
    );
    await tapVisible(tester, find.byKey(const Key('milestone_CDC-12M-LA-01')));
    await tapVisible(tester, find.byKey(const Key('status_achieved')));
    await tapVisible(tester, find.byKey(const Key('saveMilestoneButton')));
    expect(find.byKey(const Key('recordError')), findsOneWidget);
    expect(
      find.textContaining("Can't be before the date of birth."),
      findsOneWidget,
    );
    expect(find.byKey(const Key('milestoneRecorded')), findsNothing);
  });

  testWidgets('a failed search can be retried; empty results say so', (
    tester,
  ) async {
    var calls = 0;
    await openMilestoneScreen(
      tester,
      onSearch: (request) async => ++calls == 1
          ? json({'detail': 'boom'}, 500)
          : json(searchCatalogue(request.url)),
    );
    expect(
      find.text('The server had a problem (500). Please try again shortly.'),
      findsOneWidget,
    );
    await tapVisible(tester, find.byKey(const Key('retrySearchButton')));
    expect(visibleMilestoneKeys(tester), hasLength(4));

    await tester.enterText(
      find.byKey(const Key('milestoneSearchField')).last,
      'juggles',
    );
    await tester.pump(const Duration(milliseconds: 400));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('noResults')), findsOneWidget);
  });
}
