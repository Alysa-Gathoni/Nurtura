import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/state/engagement.dart';
import 'package:nurtura_app/state/preferences.dart';
import 'package:nurtura_app/state/recommendation_cache.dart';

import 'helpers.dart';
import 'recommendations_screen_test.dart' as recs;

const completionPath = '/api/recommendations/1/completion/';
const feedbackPath = '/api/recommendations/1/feedback/';

/// A backend serving one card and accepting completion and feedback.
FakeBackend progressBackend({
  Map<String, dynamic>? card,
  http.Response Function(http.Request)? onFeedback,
  bool offlineWrites = false,
}) => FakeBackend((r) async {
  if (r.url.path == recs.path) {
    return json(recs.batch([card ?? recs.card('ACT-0004', 'Peekaboo')]));
  }
  if (offlineWrites) throw http.ClientException('offline');
  if (r.url.path == completionPath) {
    if (r.method == 'DELETE') return http.Response('', 204);
    final status = jsonDecode(r.body)['status'];
    return json({'status': status, 'completion_date': '2026-10-14'}, 201);
  }
  if (r.url.path == feedbackPath) {
    if (onFeedback != null) return onFeedback(r);
    final body = jsonDecode(r.body) as Map<String, dynamic>;
    return json({...body, 'date_submitted': '2026-10-14T10:00:00Z'}, 201);
  }
  return http.Response('', 404);
});

Future<void> openDetail(
  WidgetTester tester,
  FakeBackend backend, {
  RecommendationCache? cache,
  EngagementState? engagement,
}) async {
  await recs.pumpScreen(tester, backend, cache: cache, engagement: engagement);
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(const Key('recommendation_ACT-0004')));
  await tester.pumpAndSettle();
}

/// Scrolls the detail screen until [finder] is built and visible, then taps.
Future<void> tapOnDetail(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(
    finder,
    200,
    scrollable: find
        .descendant(
          of: find.byKey(const Key('activityDetail')),
          matching: find.byType(Scrollable),
        )
        .first, // the list itself; the comment field has its own
  );
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Future<void> back(WidgetTester tester) async {
  await tester.pageBack();
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('marking done saves it, celebrates and shows on the card', (
    tester,
  ) async {
    final backend = progressBackend();
    final cache = MemoryRecommendationCache();
    final engagement = EngagementState(MemoryPreferences());
    await openDetail(tester, backend, cache: cache, engagement: engagement);

    await tapOnDetail(tester, find.byKey(const Key('markDoneButton')));
    expect(backend.to(completionPath).single.method, 'PUT');
    expect(jsonDecode(backend.to(completionPath).single.body), {
      'status': 'completed',
    });
    expect(find.text('Done on 14 Oct 2026'), findsOneWidget);
    expect(find.textContaining('Well done!'), findsOneWidget);
    expect(find.textContaining("It won't come up again"), findsOneWidget);
    expect(engagement.checkedInToday, isTrue);

    await back(tester);
    expect(find.byKey(const Key('doneChip_ACT-0004')), findsOneWidget);
    // The offline copy has it too.
    final saved = await cache.read(3);
    expect(saved!.batch.items.single.completion!.partial, isFalse);
  });

  testWidgets('partly done, then undo', (tester) async {
    final backend = progressBackend();
    await openDetail(tester, backend);

    await tapOnDetail(tester, find.byKey(const Key('markPartlyButton')));
    expect(jsonDecode(backend.to(completionPath).single.body), {
      'status': 'partially_completed',
    });
    expect(find.text('Partly done on 14 Oct 2026'), findsOneWidget);

    await tapOnDetail(tester, find.byKey(const Key('undoDoneButton')));
    expect(backend.to(completionPath).last.method, 'DELETE');
    expect(find.byKey(const Key('markDoneButton')), findsOneWidget);

    await back(tester);
    expect(find.byKey(const Key('doneChip_ACT-0004')), findsNothing);
  });

  testWidgets('feedback needs a star, then sends rating and comment', (
    tester,
  ) async {
    final backend = progressBackend();
    await openDetail(tester, backend);

    await tapOnDetail(tester, find.byKey(const Key('sendFeedbackButton')));
    expect(find.text('Tap a star to rate the activity.'), findsOneWidget);
    expect(backend.to(feedbackPath), isEmpty);

    await tapOnDetail(tester, find.byKey(const Key('star_4')));
    await tester.enterText(
      find.byKey(const Key('feedbackComment')),
      '  She giggled the whole time ',
    );
    await tapOnDetail(tester, find.byKey(const Key('sendFeedbackButton')));

    expect(jsonDecode(backend.to(feedbackPath).single.body), {
      'rating': 4,
      'comment': 'She giggled the whole time',
    });
    expect(find.text('Thanks for your feedback!'), findsOneWidget);
    expect(find.text('“She giggled the whole time”'), findsOneWidget);

    await back(tester);
    expect(find.byKey(const Key('ratingChip_ACT-0004')), findsOneWidget);
    expect(find.text('4/5'), findsOneWidget);
  });

  testWidgets('saved feedback can be edited and is sent again', (tester) async {
    final card = {
      ...recs.card('ACT-0004', 'Peekaboo'),
      'feedback': {
        'rating': 2,
        'comment': 'Too hard',
        'date_submitted': '2026-10-13T10:00:00Z',
      },
      'completion': {
        'status': 'partially_completed',
        'completion_date': '2026-10-13',
      },
    };
    final backend = progressBackend(card: card);
    await openDetail(tester, backend);

    expect(find.text('Partly done on 13 Oct 2026'), findsOneWidget);
    await tapOnDetail(tester, find.byKey(const Key('editFeedbackButton')));
    expect(find.text('Update feedback'), findsOneWidget);
    await tapOnDetail(tester, find.byKey(const Key('star_5')));
    await tapOnDetail(tester, find.byKey(const Key('sendFeedbackButton')));
    expect(jsonDecode(backend.to(feedbackPath).single.body), {
      'rating': 5,
      'comment': 'Too hard',
    });
    expect(find.text('Thanks for your feedback!'), findsOneWidget);
  });

  testWidgets('server messages are shown as they come', (tester) async {
    final backend = progressBackend(
      onFeedback: (_) => json({
        'comment': ['Keep the comment to 1000 characters or fewer.'],
      }, 400),
    );
    await openDetail(tester, backend);
    await tapOnDetail(tester, find.byKey(const Key('star_3')));
    await tapOnDetail(tester, find.byKey(const Key('sendFeedbackButton')));
    expect(find.byKey(const Key('feedbackError')), findsOneWidget);
    expect(find.text('Thanks for your feedback!'), findsNothing);
  });

  testWidgets('offline, nothing is pretended to be saved', (tester) async {
    final backend = progressBackend(offlineWrites: true);
    await openDetail(tester, backend);
    await tapOnDetail(tester, find.byKey(const Key('markDoneButton')));
    expect(find.byKey(const Key('doneError')), findsOneWidget);
    expect(find.textContaining("You're offline"), findsOneWidget);
    expect(find.byKey(const Key('markDoneButton')), findsOneWidget);
  });

  testWidgets('a full card parses and survives the offline copy', (
    tester,
  ) async {
    final cache = MemoryRecommendationCache();
    final card = {
      ...recs.card('ACT-0004', 'Peekaboo'),
      'completion': {'status': 'completed', 'completion_date': '2026-10-13'},
      'feedback': {
        'rating': 5,
        'comment': '',
        'date_submitted': '2026-10-13T10:00:00Z',
      },
    };
    await recs.pumpScreen(tester, progressBackend(card: card), cache: cache);
    await tester.pumpAndSettle();
    final saved = (await cache.read(3))!.batch.items.single;
    final round = saved.toJson();
    expect(round['completion'], card['completion']);
    expect((round['feedback'] as Map)['rating'], 5);
    expect(find.byKey(const Key('doneChip_ACT-0004')), findsOneWidget);
  });
}
