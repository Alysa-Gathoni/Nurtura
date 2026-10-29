import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nurtura_app/models/recommendation.dart';
import 'package:nurtura_app/utils/dates.dart' as dates;

import 'children_screen_test.dart' show childJson, tapVisible;
import 'helpers.dart';
import 'recommendations_screen_test.dart' as recs;

const _steps =
    'Point to things you see together and name them slowly. Wait for your '
    'child to look, then say the word again. Let them try to copy you.';

/// A card with the full activity, as the API sends it since #138.
Map<String, dynamic> fullCard({String materials = 'A few household objects'}) =>
    {
      ...recs.card('ACT-0004', 'Naming Everyday Objects'),
      'description': _steps,
      'materials': materials,
      'cultural_relevance': 'Works with whatever is in your kitchen.',
      'source': 'CDC',
      'source_url': 'https://www.cdc.gov/act-early/',
    };

Future<void> openDetail(WidgetTester tester, Map<String, dynamic> card) async {
  final backend = FakeBackend((r) async => json(recs.batch([card])));
  await recs.pumpScreen(tester, backend);
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(const Key('recommendation_ACT-0004')));
  await tester.pumpAndSettle();
}

void main() {
  group('activity details (#138)', () {
    testWidgets('shows the full steps, materials, home note and source', (
      tester,
    ) async {
      await openDetail(tester, fullCard());

      expect(find.text(_steps), findsOneWidget);
      expect(find.text('Name things you see together.'), findsNothing);
      expect(find.text("What you'll need"), findsOneWidget);
      expect(find.text('A few household objects'), findsOneWidget);
      expect(find.text('Making it work at home'), findsOneWidget);
      expect(
        find.text('Works with whatever is in your kitchen.'),
        findsOneWidget,
      );
      final source = find.byKey(const Key('activitySource'));
      await tester.scrollUntilVisible(source, 200);
      expect(
        tester.widget<Text>(source).data,
        'Based on guidance from CDC (cdc.gov).',
      );
    });

    testWidgets('"None" for materials reads as nothing special', (
      tester,
    ) async {
      await openDetail(tester, fullCard(materials: 'None'));

      expect(find.text('Nothing special: just you and Amani.'), findsOneWidget);
      expect(find.text('None'), findsNothing);
    });

    testWidgets('an idea saved before #138 still opens, with the short text', (
      tester,
    ) async {
      await openDetail(
        tester,
        recs.card('ACT-0004', 'Naming Everyday Objects'),
      );

      expect(find.text('Name things you see together.'), findsWidgets);
      expect(find.byKey(const Key('materials')), findsNothing);
      expect(find.byKey(const Key('atHome')), findsNothing);
      expect(find.byKey(const Key('activitySource')), findsNothing);
    });

    test('the full activity survives the offline copy', () {
      final original = Recommendation.fromJson(fullCard());
      final copy = Recommendation.fromJson(original.toJson());
      expect(copy.description, _steps);
      expect(copy.materials, 'A few household objects');
      expect(copy.culturalRelevance, original.culturalRelevance);
      expect(copy.source, 'CDC');
      expect(copy.sourceUrl, 'https://www.cdc.gov/act-early/');
      expect(
        original.withProgress(feedback: null).description,
        original.description,
      );
    });
  });

  group('polish (#138)', () {
    setUpAll(() => WidgetController.hitTestWarningShouldBeFatal = true);
    setUp(() => dates.clock = () => DateTime(2026, 10, 1, 9));
    tearDown(() => dates.clock = DateTime.now);

    testWidgets('choosing a date leaves the name field unfocused', (
      tester,
    ) async {
      await pumpApp(
        tester,
        FakeBackend((_) async => json(caregiverJson)),
        savedToken: 'tok',
      );
      await tapVisible(tester, find.byKey(const Key('addChildButton')));
      final name = find.byKey(const Key('childNameField')).last;
      await tester.tap(name);
      await tester.enterText(name, 'Amani');
      await tapVisible(tester, find.byKey(const Key('dateField')));
      await tester.tap(find.text('OK'));
      await tester.pumpAndSettle();

      final editable = tester.widget<EditableText>(
        find.descendant(of: name, matching: find.byType(EditableText)),
      );
      expect(editable.focusNode.hasFocus, isFalse);
      expect(find.text('1 Apr 2026'), findsOneWidget);
    });

    testWidgets('Family shows who is signed in', (tester) async {
      await pumpApp(
        tester,
        FakeBackend((_) async => json(caregiverJson), children: [childJson()]),
        savedToken: 'tok',
      );
      await tapVisible(tester, find.byKey(const Key('tab_family')));

      expect(find.byKey(const Key('accountCard')), findsOneWidget);
      expect(find.text('wanjiru@example.com'), findsOneWidget);
    });
  });
}
