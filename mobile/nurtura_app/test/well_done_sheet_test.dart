import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'activity_progress_test.dart' as progress;
import 'helpers.dart';
import 'recommendations_screen_test.dart' as recs;

const observablePath = '/api/recommendations/1/observable/';

/// One card; marking done, feedback, and two skills to observe.
FakeBackend wellDoneBackend() => FakeBackend((r) async {
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
          'description': 'Makes a lot of different sounds',
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

Future<void> tapInSheet(WidgetTester tester, String key) async {
  await tester.ensureVisible(find.byKey(Key(key)));
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(Key(key)));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('the sheet saves interest, outcome and skills seen (#185)', (
    tester,
  ) async {
    final backend = wellDoneBackend();
    await progress.openDetail(tester, backend);
    await progress.tapOnDetail(tester, find.byKey(const Key('markDoneButton')));

    expect(find.text('Well done!'), findsOneWidget);
    expect(find.text('How did “Peekaboo” go with Amani?'), findsOneWidget);
    expect(find.text('Makes a lot of different sounds'), findsOneWidget);

    await tapInSheet(tester, 'saveProgressButton');
    expect(find.text('Choose how it went.'), findsOneWidget);
    expect(backend.to(progress.feedbackPath), isEmpty);

    await tapInSheet(tester, 'interest_loved_it');
    await tapInSheet(tester, 'sheetOutcome_went_well');
    expect(find.text('What got in the way?'), findsNothing);
    await tapInSheet(tester, 'skill_CDC-09M-LA-01');
    await tester.enterText(
      find.byKey(const Key('wellDoneNote')),
      'Lots of babble',
    );
    await tapInSheet(tester, 'saveProgressButton');

    expect(jsonDecode(backend.to(progress.feedbackPath).single.body), {
      'rating': null,
      'comment': 'Lots of babble',
      'outcome': 'went_well',
      'issues': <String>[],
      'interest': 'loved_it',
      'observed': ['CDC-09M-LA-01'],
    });
    expect(find.byKey(const Key('wellDoneSheet')), findsNothing);
    expect(find.byKey(const Key('milestonesRecordedSnack')), findsOneWidget);
    expect(find.text('Interest: Loved it'), findsOneWidget);

    // The profile changed, so going back asks for a fresh batch.
    await progress.back(tester);
    expect(backend.to(recs.path).last.method, 'POST');
  });

  testWidgets("didn't work asks what got in the way", (tester) async {
    final backend = wellDoneBackend();
    await progress.openDetail(tester, backend);
    await progress.tapOnDetail(tester, find.byKey(const Key('markDoneButton')));
    await tapInSheet(tester, 'interest_bored');
    await tapInSheet(tester, 'sheetOutcome_didnt_work');
    await tapInSheet(tester, 'sheetIssue_too_hard');
    await tapInSheet(tester, 'saveProgressButton');
    final sent = jsonDecode(backend.to(progress.feedbackPath).single.body);
    expect(sent['issues'], ['too_hard']);
    expect(sent['interest'], 'bored');
    // Nothing recorded, so the ideas aren't refreshed.
    expect(find.byKey(const Key('milestonesRecordedSnack')), findsNothing);
    await progress.back(tester);
    expect(backend.to(recs.path).map((r) => r.method), ['GET']);
  });
}
