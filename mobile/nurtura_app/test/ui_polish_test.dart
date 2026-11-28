import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'activity_progress_test.dart' as progress;
import 'children_screen_test.dart' show childJson;
import 'helpers.dart';
import 'recommendations_screen_test.dart' as recs;

void main() {
  testWidgets('a form error goes once the field is filled in (#293)', (
    tester,
  ) async {
    await pumpApp(tester, FakeBackend((r) async => json(caregiverJson)));
    await tester.ensureVisible(find.byKey(const Key('submitButton')));
    await tester.tap(find.byKey(const Key('submitButton')));
    await tester.pumpAndSettle();
    expect(find.text('Enter your email address.'), findsOneWidget);

    await tester.enterText(
      find.byKey(const Key('emailField')).last,
      'demo.caregiver@example.com',
    );
    await tester.pumpAndSettle();
    expect(find.text('Enter your email address.'), findsNothing);
    // The other field, still empty, keeps its error.
    expect(find.text('Enter your password.'), findsOneWidget);
  });

  testWidgets('choosing how it went doesn\'t move the chips (#293)', (
    tester,
  ) async {
    await progress.openDetail(tester, progress.progressBackend());
    await progress.tapOnDetail(tester, find.byKey(const Key('markDoneButton')));
    for (final key in ['went_well', 'partly', 'didnt_work']) {
      final chip = tester.widget<ChoiceChip>(
        find.byKey(Key('sheetOutcome_$key')),
      );
      expect(chip.showCheckmark, isFalse);
    }
  });

  testWidgets('tapping the open tab goes back to the top (#293)', (
    tester,
  ) async {
    final backend = FakeBackend((r) async {
      if (r.url.path.endsWith('/recommendations/')) {
        return json(
          recs.batch([
            for (var i = 1; i <= 5; i++)
              recs.card('ACT-000$i', 'Idea $i', position: i),
          ]),
        );
      }
      return json(caregiverJson);
    }, children: [childJson()]);
    await pumpApp(tester, backend, savedToken: 'tok');
    final list = find.byType(Scrollable).first;
    await tester.drag(list, const Offset(0, -900));
    await tester.pumpAndSettle();
    final scrolled = tester.state<ScrollableState>(list).position.pixels;
    expect(scrolled, greaterThan(0));

    await tester.tap(find.byKey(const Key('tab_today')));
    await tester.pumpAndSettle();
    expect(tester.state<ScrollableState>(list).position.pixels, 0);
  });
}
