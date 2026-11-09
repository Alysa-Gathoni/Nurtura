import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';
import 'milestone_screen_test.dart' as ms;

const trackerPath = '/api/children/3/tracker/';
const observationPath = '/api/children/3/observation/';

Map<String, dynamic> trackerJson({String waveStatus = ''}) => {
  'age_months': 13.0,
  'prenatal': false,
  'areas': [
    {
      'domain': 'Motor',
      'milestones': [
        {
          'id': 3,
          'key': 'CDC-09M-MO-04',
          'description': 'Sits without support',
          'source': 'CDC',
          'expected_age_months': 9.0,
          'due': true,
          'status': 'achieved',
          'observed_on': '2026-06-01',
          'observed_at_months': 9,
        },
      ],
    },
    {'domain': 'Socio-Emotional', 'milestones': []},
    {
      'domain': 'Language',
      'milestones': [
        {
          'id': 1,
          'key': 'CDC-12M-LA-01',
          'description': 'Waves "bye-bye"',
          'source': 'CDC',
          'expected_age_months': 12.0,
          'due': true,
          'status': waveStatus,
          'observed_on': null,
          'observed_at_months': null,
        },
      ],
    },
    {'domain': 'Cognitive', 'milestones': []},
  ],
};

/// The app on the Milestones tab, with a tracker and an observation.
Future<FakeBackend> openTracker(WidgetTester tester) async {
  tester.view.physicalSize = const Size(420, 1400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  var recorded = '';
  final backend = FakeBackend((r) async {
    if (r.url.path == trackerPath) {
      return json(trackerJson(waveStatus: recorded));
    }
    if (r.url.path == observationPath) {
      return json({
        'sentences': [],
        'text': 'This week Amani tried 2 activities, and 2 went well.',
        'focus_domain': 'Language',
      });
    }
    if (r.url.path == '/api/children/3/milestones/' && r.method == 'POST') {
      recorded = jsonDecode(r.body)['status'] as String;
      return json(ms.recordedResponse(recorded), 201);
    }
    if (r.url.path == '/api/reference-milestones/') {
      return json(ms.searchCatalogue(r.url));
    }
    if (r.url.path == '/api/children/3/recommendations/') {
      return json({'batch': null, 'generated_at': null, 'recommendations': []});
    }
    return json(caregiverJson); // the signed-in account
  }, children: [ms.child]);
  await pumpApp(tester, backend, savedToken: 'tok');
  await tester.tap(find.byKey(const Key('tab_milestones')));
  await tester.pumpAndSettle();
  return backend;
}

Future<void> tapArea(WidgetTester tester, String domain) async {
  final chip = find.byKey(Key('trackerArea_$domain'));
  await tester.ensureVisible(chip);
  await tester.pumpAndSettle();
  await tester.tap(chip);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('opens on the tracker with the observation (#192)', (
    tester,
  ) async {
    await openTracker(tester);
    expect(find.byKey(const Key('observationCard')), findsOneWidget);
    expect(
      find.text('This week Amani tried 2 activities, and 2 went well.'),
      findsOneWidget,
    );
    // The first area, Moving, is shown.
    expect(find.text('Sits without support'), findsOneWidget);
    expect(find.text('Achieved at 9 months'), findsOneWidget);
  });

  testWidgets('switching area shows its milestones and status', (tester) async {
    await openTracker(tester);
    await tapArea(tester, 'Language');
    expect(find.text('Waves "bye-bye"'), findsOneWidget);
    expect(
      find.text('Most often seen by 12 months · not recorded'),
      findsOneWidget,
    );
    await tapArea(tester, 'Socio-Emotional');
    expect(find.byKey(const Key('trackerEmpty')), findsOneWidget);
  });

  testWidgets('tapping a milestone records a new status', (tester) async {
    final backend = await openTracker(tester);
    await tapArea(tester, 'Language');
    await tester.tap(find.byKey(const Key('tracker_CDC-12M-LA-01')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('setStatus_emerging')));
    await tester.pumpAndSettle();

    final post = backend.requests.lastWhere(
      (r) => r.url.path == '/api/children/3/milestones/',
    );
    expect(jsonDecode(post.body), {'reference': 1, 'status': 'emerging'});
    expect(find.byKey(const Key('trackerSaved')), findsOneWidget);
    // Reloaded with the new status.
    expect(find.textContaining('Starting'), findsWidgets);
  });

  testWidgets('"Log another milestone" opens the picker', (tester) async {
    await openTracker(tester);
    await tester.ensureVisible(find.byKey(const Key('logAnotherMilestone')));
    await tester.tap(find.byKey(const Key('logAnotherMilestone')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('milestoneSearchField')), findsOneWidget);
  });
}
