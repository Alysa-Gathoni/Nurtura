import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'activity_progress_test.dart' as progress;
import 'helpers.dart';
import 'recommendations_screen_test.dart' as recs;

const observablePath = '/api/recommendations/1/observable/';

/// One card; marking done, feedback, and two skills to observe.
FakeBackend feedbackBackend({
  String firstSkill = 'Makes a lot of different sounds',
}) => FakeBackend((r) async {
  if (r.url.path == recs.path) {
    return json(recs.batch([recs.card('ACT-0004', 'Peekaboo')]));
  }
  if (r.url.path == progress.completionPath) {
    return json({'status': 'completed', 'completion_date': '2026-11-04'}, 201);
  }
  if (r.url.path == observablePath) {
    return json({
      'skills': [
        {
          'key': 'CDC-09M-LA-01',
          'description': firstSkill,
          'expected_age_months': 9.0,
          'status': '',
        },
        {
          'key': 'CDC-12M-LA-01',
          'description': 'Waves "bye-bye"',
          'expected_age_months': 12.0,
          'status': '',
        },
      ],
    });
  }
  if (r.url.path == progress.feedbackPath) {
    final body = jsonDecode(r.body) as Map<String, dynamic>;
    return json({
      ...body,
      'date_submitted': '2026-11-04T10:00:00Z',
      'recorded': [
        if ((body['observed'] as List).isNotEmpty)
          'Makes a lot of different sounds',
      ],
    }, 201);
  }
  return http.Response('', 404);
});

Future<void> tapInSheet(WidgetTester tester, String key) =>
    progress.tapInSheet(tester, key);

void main() {
  testWidgets('long milestone names wrap instead of being clipped (#214)', (
    tester,
  ) async {
    const long =
        'Makes a lot of different sounds like "mamamama" and "bababababa"';
    await progress.openDetail(tester, feedbackBackend(firstSkill: long));
    await progress.tapOnDetail(tester, find.byKey(const Key('markDoneButton')));
    final label = tester.renderObject<RenderParagraph>(find.text(long));
    expect(label.didExceedMaxLines, isFalse);
    // More than one line: a single line was clipped at the chip's edge.
    expect(label.size.height, greaterThan(30));
  });

  testWidgets('the sheet saves interest, outcome and skills seen (#185)', (
    tester,
  ) async {
    final backend = feedbackBackend();
    await progress.openDetail(tester, backend);
    await progress.tapOnDetail(tester, find.byKey(const Key('markDoneButton')));

    expect(find.text('Well done!'), findsOneWidget);
    expect(find.text('How did “Peekaboo” go with Amani?'), findsOneWidget);
    expect(find.text('Makes a lot of different sounds'), findsOneWidget);

    await tapInSheet(tester, 'saveFeedbackButton');
    expect(find.text('Choose how it went.'), findsOneWidget);
    expect(backend.to(progress.feedbackPath), isEmpty);

    await tapInSheet(tester, 'interest_loved_it');
    await tapInSheet(tester, 'sheetOutcome_went_well');
    expect(find.text('What got in the way?'), findsNothing);
    await tapInSheet(tester, 'skill_CDC-09M-LA-01');
    await tester.enterText(
      find.byKey(const Key('feedbackNote')),
      'Lots of babble',
    );
    await tapInSheet(tester, 'saveFeedbackButton');

    expect(jsonDecode(backend.to(progress.feedbackPath).single.body), {
      'rating': null,
      'comment': 'Lots of babble',
      'outcome': 'went_well',
      'issues': <String>[],
      'interest': 'loved_it',
      'observed': ['CDC-09M-LA-01'],
    });
    expect(find.byKey(const Key('feedbackSheet')), findsNothing);
    expect(find.byKey(const Key('milestonesRecordedSnack')), findsOneWidget);
    expect(find.text('Interest: Loved it'), findsOneWidget);

    // The profile changed, so going back asks for a fresh batch.
    await progress.back(tester);
    expect(backend.to(recs.path).last.method, 'POST');
  });

  testWidgets('Edit starts from what the sheet saved (#231)', (tester) async {
    final backend = feedbackBackend();
    await progress.openDetail(tester, backend);
    await progress.tapOnDetail(tester, find.byKey(const Key('markDoneButton')));
    await tapInSheet(tester, 'interest_happy');
    await tapInSheet(tester, 'sheetOutcome_went_well');
    await tester.enterText(find.byKey(const Key('feedbackNote')), 'Giggles');
    await tapInSheet(tester, 'saveFeedbackButton');

    await progress.tapOnDetail(
      tester,
      find.byKey(const Key('editFeedbackButton')),
    );
    ChoiceChip chip(String key) =>
        tester.widget<ChoiceChip>(find.byKey(Key(key)));
    // Before #231 the outcome came back empty, and saving said
    // "Choose how it went." although it had been chosen in the sheet.
    expect(find.text('Your feedback'), findsOneWidget);
    expect(chip('sheetOutcome_went_well').selected, isTrue);
    bool picked(String key) => tester
        .widget<Semantics>(
          find
              .ancestor(
                of: find.byKey(Key(key)),
                matching: find.byType(Semantics),
              )
              .first,
        )
        .properties
        .selected!;
    expect(picked('interest_happy'), isTrue);
    expect(picked('interest_bored'), isFalse);
    expect(
      tester
          .widget<TextField>(find.byKey(const Key('feedbackNote')))
          .controller!
          .text,
      'Giggles',
    );
    // Skills seen are asked once, with new feedback, not again on Edit.
    expect(find.byKey(const Key('skill_CDC-09M-LA-01')), findsNothing);
    // Cancel leaves the saved feedback as it was.
    await tapInSheet(tester, 'skipFeedbackButton');
    expect(backend.to(progress.feedbackPath), hasLength(1));
    expect(find.text('Thanks for your feedback!'), findsOneWidget);
  });

  testWidgets("didn't work asks what got in the way", (tester) async {
    final backend = feedbackBackend();
    await progress.openDetail(tester, backend);
    await progress.tapOnDetail(tester, find.byKey(const Key('markDoneButton')));
    await tapInSheet(tester, 'interest_bored');
    await tapInSheet(tester, 'sheetOutcome_didnt_work');
    await tapInSheet(tester, 'sheetIssue_too_hard');
    await tapInSheet(tester, 'saveFeedbackButton');
    final sent = jsonDecode(backend.to(progress.feedbackPath).single.body);
    expect(sent['issues'], ['too_hard']);
    expect(sent['interest'], 'bored');
    // Nothing recorded, so the ideas aren't refreshed.
    expect(find.byKey(const Key('milestonesRecordedSnack')), findsNothing);
    await progress.back(tester);
    expect(backend.to(recs.path).map((r) => r.method), ['GET']);
  });
}
