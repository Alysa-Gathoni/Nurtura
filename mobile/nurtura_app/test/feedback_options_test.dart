import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/state/recommendation_cache.dart';

import 'activity_progress_test.dart' as progress;
import 'helpers.dart';
import 'recommendations_screen_test.dart' as recs;

const optionsPath = '/api/recommendations/1/options/';

Map<String, dynamic> option(String id, String name, {String tip = ''}) => {
  'reason': 'no_materials',
  'title': 'Needs nothing special',
  'why':
      "You didn't have the materials for “Peekaboo”; this one needs "
      'nothing special.',
  'tip': tip,
  'activity': {
    'activity_id': id,
    'activity_name': name,
    'developmental_domain': 'Language',
    'age_range': '6-12 months',
    'short_description': 'Talk as you cook.',
    'description': 'Talk as you cook.',
    'materials': 'None',
    'cultural_relevance': '',
    'source': 'CDC',
    'source_url': '',
  },
};

/// One card, feedback, and options; choosing returns a batch with the
/// chosen activity pinned first.
FakeBackend optionsBackend({Map<String, dynamic>? card}) =>
    FakeBackend((r) async {
      if (r.url.path == recs.path) {
        return json(recs.batch([card ?? recs.card('ACT-0004', 'Peekaboo')]));
      }
      if (r.url.path == progress.feedbackPath) {
        final body = jsonDecode(r.body) as Map<String, dynamic>;
        return json({...body, 'date_submitted': '2026-11-03T10:00:00Z'}, 201);
      }
      if (r.url.path == optionsPath && r.method == 'GET') {
        return json({
          'options': [
            option(
              'ACT-0903',
              'Talk About Your Day',
              tip: 'Try again another day.',
            ),
          ],
        });
      }
      if (r.url.path == optionsPath && r.method == 'POST') {
        final chosen = jsonDecode(r.body)['activity_id'];
        return json({
          ...recs.batch([
            {
              ...recs.card(chosen as String, 'Talk About Your Day'),
              'batch': 'b-2',
              'pinned': true,
            },
            {...recs.card('ACT-0031', 'Naming Pictures', position: 2)},
          ]),
          'batch': 'b-2',
        }, 201);
      }
      return http.Response('', 404);
    });

void main() {
  testWidgets('after feedback, options are offered and one can be added', (
    tester,
  ) async {
    final cache = MemoryRecommendationCache();
    final backend = optionsBackend();
    await progress.openDetail(tester, backend, cache: cache);
    expect(find.byKey(const Key('feedbackOptions')), findsNothing);

    await progress.tapOnDetail(
      tester,
      find.byKey(const Key('outcome_didnt_work')),
    );
    await progress.tapOnDetail(
      tester,
      find.byKey(const Key('issue_no_materials')),
    );
    await progress.tapOnDetail(tester, find.byKey(const Key('star_2')));
    await progress.tapOnDetail(
      tester,
      find.byKey(const Key('sendFeedbackButton')),
    );

    expect(find.text('What next?'), findsOneWidget);
    expect(find.text('Needs nothing special'), findsOneWidget);
    expect(find.text('Talk About Your Day'), findsOneWidget);
    expect(find.byKey(const Key('optionTip_ACT-0903')), findsOneWidget);

    await progress.tapOnDetail(
      tester,
      find.byKey(const Key('chooseOption_ACT-0903')),
    );
    expect(jsonDecode(backend.to(optionsPath).last.body), {
      'activity_id': 'ACT-0903',
    });

    // Back on the list: the new batch, the choice first and marked.
    expect(find.byKey(const Key('activityDetail')), findsNothing);
    expect(find.text("Added to Amani's ideas."), findsOneWidget);
    expect(find.byKey(const Key('pinnedChip_ACT-0903')), findsOneWidget);
    expect(find.text('Your choice'), findsOneWidget);
    expect((await cache.read(3))!.batch.items.first.pinned, isTrue);
  });

  testWidgets('saved feedback with an outcome shows its options on opening', (
    tester,
  ) async {
    final card = {
      ...recs.card('ACT-0004', 'Peekaboo'),
      'feedback': {
        'rating': 2,
        'comment': '',
        'outcome': 'didnt_work',
        'issues': ['no_materials'],
        'date_submitted': '2026-11-02T10:00:00Z',
      },
    };
    await progress.openDetail(tester, optionsBackend(card: card));
    await tester.scrollUntilVisible(
      find.byKey(const Key('option_ACT-0903')),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.byKey(const Key('option_ACT-0903')), findsOneWidget);
  });

  testWidgets('saved feedback without an outcome asks for no options', (
    tester,
  ) async {
    final card = {
      ...recs.card('ACT-0004', 'Peekaboo'),
      'feedback': {
        'rating': 4,
        'comment': '',
        'date_submitted': '2026-10-02T10:00:00Z',
      },
    };
    final backend = optionsBackend(card: card);
    await progress.openDetail(tester, backend);
    expect(backend.to(optionsPath), isEmpty);
    expect(find.byKey(const Key('feedbackOptions')), findsNothing);
  });
}
