import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

void main() {
  testWidgets('dates are British and weeks start on Monday (#293)', (
    tester,
  ) async {
    await pumpApp(tester, FakeBackend((r) async => json(caregiverJson)));
    final context = tester.element(find.byType(Scaffold).first);
    final words = MaterialLocalizations.of(context);
    // The date picker's own words: "Thu 25 Feb", not "Thu, Feb 25".
    expect(words.formatMediumDate(DateTime(2027, 2, 25)), 'Thu 25 Feb');
    // Monday first, like the weekly plan (index 0 is Sunday).
    expect(words.firstDayOfWeekIndex, 1);
  });
}
