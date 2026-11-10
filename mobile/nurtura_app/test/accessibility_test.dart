// Accessibility checks (NFR-07, #206): Flutter's Android tap-target, labelled
// tap-target and text-contrast guidelines on every caregiver tab, in light
// and dark themes, and every tab at twice the text size without overflow.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nurtura_app/state/preferences.dart';

import 'explore_screen_test.dart' as explore;
import 'helpers.dart';
import 'milestone_screen_test.dart' as ms;
import 'milestone_tracker_test.dart' as tracker;
import 'recommendations_screen_test.dart' as recs;

const tabs = [
  'tab_today',
  'tab_explore',
  'tab_progress',
  'tab_milestones',
  'tab_family',
];

FakeBackend backend() => FakeBackend((r) async {
  final path = r.url.path;
  if (path == recs.path) {
    return json(
      recs.batch([
        recs.card('ACT-0001', 'Peekaboo'),
        recs.card('ACT-0002', 'Tummy Time'),
      ]),
    );
  }
  if (path == tracker.trackerPath) return json(tracker.trackerJson());
  if (path == tracker.observationPath) {
    return json({
      'sentences': [],
      'text': 'This week Amani tried 2 activities, and 2 went well.',
      'focus_domain': 'Language',
    });
  }
  if (path == explore.listPath) {
    return json({
      'query': '',
      'results': [
        explore.activity('ACT-0001', 'Splash Time'),
        explore.activity('ACT-0004', 'Peekaboo', saved: true),
      ],
    });
  }
  if (path == '/api/children/3/milestones/') return json([]);
  if (path == '/api/reference-milestones/') {
    return json(ms.searchCatalogue(r.url));
  }
  return json(caregiverJson);
}, children: [ms.child]);

/// A typical Android phone: 412 × 915 logical pixels.
void phone(WidgetTester tester, {double textScale = 1.0}) {
  tester.view.physicalSize = const Size(1236, 2745);
  tester.view.devicePixelRatio = 3.0;
  tester.platformDispatcher.textScaleFactorTestValue = textScale;
  addTearDown(tester.view.reset);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
}

Future<void> openTab(WidgetTester tester, String tab) async {
  final button = find.byKey(Key(tab));
  await tester.ensureVisible(button);
  await tester.pumpAndSettle();
  await tester.tap(button);
  await tester.pumpAndSettle();
}

Future<void> meetsAll(WidgetTester tester, String where) async {
  for (final guideline in [
    androidTapTargetGuideline,
    labeledTapTargetGuideline,
    textContrastGuideline,
  ]) {
    await expectLater(tester, meetsGuideline(guideline), reason: where);
  }
}

void main() {
  for (final theme in ['light', 'dark']) {
    testWidgets('every tab meets the guidelines ($theme theme)', (
      tester,
    ) async {
      final semantics = tester.ensureSemantics();
      phone(tester);
      await pumpApp(
        tester,
        backend(),
        savedToken: 'tok',
        preferences: MemoryPreferences({'nurtura.themeMode': theme}),
      );
      for (final tab in tabs) {
        await openTab(tester, tab);
        await meetsAll(tester, '$tab, $theme');
      }
      semantics.dispose();
    });
  }

  testWidgets('the sign-in screen meets the guidelines', (tester) async {
    final semantics = tester.ensureSemantics();
    phone(tester);
    await pumpApp(tester, FakeBackend((r) async => json({})));
    await meetsAll(tester, 'sign-in');
    semantics.dispose();
  });

  testWidgets('every tab works at twice the text size', (tester) async {
    phone(tester, textScale: 2.0);
    await pumpApp(tester, backend(), savedToken: 'tok');
    for (final tab in tabs) {
      await openTab(tester, tab);
      expect(tester.takeException(), isNull, reason: tab);
    }
  });

  testWidgets('the sign-in screen works at twice the text size', (
    tester,
  ) async {
    phone(tester, textScale: 2.0);
    await pumpApp(tester, FakeBackend((r) async => json({})));
    expect(tester.takeException(), isNull);
  });
}
