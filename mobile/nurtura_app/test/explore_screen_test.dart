import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'helpers.dart';
import 'milestone_screen_test.dart' as ms;
import 'recommendations_screen_test.dart' as recs;

const listPath = '/api/children/3/activities/';

Map<String, dynamic> activity(String id, String name, {bool saved = false}) => {
  'activity_id': id,
  'activity_name': name,
  'developmental_domain': 'Sensory',
  'age_range': '6-12 months',
  'short_description': 'Splash and pour together.',
  'description': 'Splash and pour together in a basin.',
  'materials': 'None',
  'cultural_relevance': 'A sufuria works well.',
  'source': 'Pathways.org',
  'source_url': '',
  'saved': saved,
};

/// The app on the Explore tab, for a child who likes water.
Future<FakeBackend> openExplore(WidgetTester tester) async {
  tester.view.physicalSize = const Size(420, 1600);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  final backend = FakeBackend(
    (r) async {
      final q = r.url.queryParameters;
      if (r.url.path == listPath) {
        if (q['for'] == 'interests') {
          return json({
            'query': 'Activities for a child who enjoys water',
            'results': [activity('ACT-0001', 'Splash Time')],
          });
        }
        if (q['saved'] == '1') {
          return json({
            'query': '',
            'results': [activity('ACT-0002', 'Saved Song', saved: true)],
          });
        }
        if ((q['q'] ?? '').isNotEmpty) {
          return json({
            'query': q['q'],
            'results': [activity('ACT-0003', 'Water Pouring')],
          });
        }
        return json({
          'query': '',
          'results': [
            activity('ACT-0001', 'Splash Time'),
            activity('ACT-0004', 'Peekaboo'),
          ],
        });
      }
      if (r.url.path.startsWith('/api/children/3/saved/')) {
        return r.method == 'DELETE'
            ? http.Response('', 204)
            : json({'activity_id': 'x', 'saved': true}, 201);
      }
      if (r.url.path == '/api/children/3/activities/ACT-0004/try/') {
        return json(
          recs.batch([
            {...recs.card('ACT-0004', 'Peekaboo'), 'pinned': true},
          ]),
          201,
        );
      }
      if (r.url.path == recs.path) {
        return json(
          recs.batch([
            {...recs.card('ACT-0004', 'Peekaboo'), 'pinned': true},
          ]),
        );
      }
      return json(caregiverJson);
    },
    children: [
      {
        ...ms.child,
        'interests': ['water'],
      },
    ],
  );
  await pumpApp(tester, backend, savedToken: 'tok');
  await tester.tap(find.byKey(const Key('tab_explore')));
  await tester.pumpAndSettle();
  return backend;
}

void main() {
  testWidgets('shows interests, saved and all ideas (#194)', (tester) async {
    await openExplore(tester);
    expect(find.text("Based on Amani's interests"), findsOneWidget);
    expect(find.text('Saved for later'), findsOneWidget);
    expect(find.text('All ideas for Amani'), findsOneWidget);
    expect(find.text('Saved Song'), findsOneWidget);
    expect(find.text('Peekaboo'), findsOneWidget);
  });

  testWidgets('searching asks the server and shows results', (tester) async {
    final backend = await openExplore(tester);
    await tester.enterText(
      find.byKey(const Key('exploreSearch')),
      'messy play with water',
    );
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pumpAndSettle();
    expect(
      backend.requests.last.url.queryParameters['q'],
      'messy play with water',
    );
    expect(find.text('Results'), findsOneWidget);
    expect(find.text('Water Pouring'), findsOneWidget);
    expect(find.text('Saved for later'), findsNothing);
  });

  testWidgets('saving and unsaving call the server', (tester) async {
    final backend = await openExplore(tester);
    await tester.tap(find.byKey(const Key('save_ACT-0004')));
    await tester.pumpAndSettle();
    expect(backend.requests.last.url.path, '/api/children/3/saved/ACT-0004/');
    expect(backend.requests.last.method, 'PUT');
    await tester.tap(find.byKey(const Key('save_ACT-0002')));
    await tester.pumpAndSettle();
    expect(backend.requests.last.method, 'DELETE');
  });

  testWidgets('"Try this" adds it to the ideas and opens Today', (
    tester,
  ) async {
    final backend = await openExplore(tester);
    await tester.tap(find.byKey(const Key('explore_ACT-0004')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('exploreSheet')), findsOneWidget);
    expect(find.text('A sufuria works well.'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('tryActivityButton')));
    await tester.tap(find.byKey(const Key('tryActivityButton')));
    await tester.pumpAndSettle();
    expect(
      backend.requests.any(
        (r) =>
            r.method == 'POST' &&
            r.url.path == '/api/children/3/activities/ACT-0004/try/',
      ),
      isTrue,
    );
    expect(find.byKey(const Key('exploreSheet')), findsNothing);
    // Today shows the idea, marked as chosen.
    expect(find.byKey(const Key('pinnedChip_ACT-0004')), findsOneWidget);
  });
}
