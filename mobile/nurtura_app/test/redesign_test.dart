import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nurtura_app/logic/progress.dart';
import 'package:nurtura_app/models/reference_milestone.dart';
import 'package:nurtura_app/state/engagement.dart';
import 'package:nurtura_app/state/preferences.dart';
import 'package:nurtura_app/state/theme_state.dart';
import 'package:nurtura_app/utils/dates.dart' as dates;

import 'children_screen_test.dart' show childJson, tapVisible;
import 'helpers.dart';
import 'recommendations_screen_test.dart' as recs;

MilestoneObservation obs(
  String domain,
  String description,
  MilestoneStatus status, [
  String date = '2026-09-01',
]) => MilestoneObservation(
  domain: domain,
  description: description,
  status: status,
  observationDate: DateTime.parse(date),
);

Map<String, dynamic> obsJson(
  String domain,
  String description,
  String status,
) => {
  'id': description.hashCode,
  'reference': 1,
  'reference_key': 'X',
  'domain': domain,
  'description': description,
  'status': status,
  'observation_date': '2026-09-20',
  'created_at': '2026-09-20T09:00:00Z',
};

void main() {
  setUp(() => dates.clock = () => DateTime(2026, 10, 1, 9));
  tearDown(() => dates.clock = DateTime.now);

  group('progress summary', () {
    test('counts each milestone once, by its latest observation', () {
      final summary = summarise(
        [
          obs('Language', 'Waves', MilestoneStatus.notYet, '2026-08-01'),
          obs('Language', 'Waves', MilestoneStatus.achieved, '2026-09-01'),
          obs('Motor', 'Walks', MilestoneStatus.emerging),
        ],
        streak: 0,
        bestStreak: 0,
      );
      final language = summary.areas.firstWhere((a) => a.domain == 'Language');
      expect(language.celebrated, 1);
      expect(language.practising, 0);
      expect(summary.celebrated, 1);
      expect(summary.recorded, 2);
      expect(summary.areas, hasLength(5)); // every area, even empty
    });

    test('badges unlock from the caregiver’s own records and streak', () {
      ProgressSummary s(int n, {int streak = 0, int best = 0}) => summarise(
        [
          for (var i = 0; i < n; i++)
            obs(
              ['Language', 'Motor', 'Cognitive'][i % 3],
              'm$i',
              i == 0 ? MilestoneStatus.achieved : MilestoneStatus.notYet,
            ),
        ],
        streak: streak,
        bestStreak: best,
      );
      Set<String> unlocked(ProgressSummary x) =>
          x.badges.where((b) => b.unlocked).map((b) => b.id).toSet();

      expect(unlocked(s(0)), isEmpty);
      expect(unlocked(s(1)), {'first_step', 'celebration'});
      expect(unlocked(s(3)), {'first_step', 'celebration', 'explorer'});
      expect(unlocked(s(5)), contains('keen_observer'));
      expect(unlocked(s(0, best: 3)), {'streak_3'});
      expect(unlocked(s(0, streak: 7)), {'streak_3', 'streak_7'});
    });

    test('nothing compares the child with norms or other children', () {
      final summary = summarise(
        [obs('Language', 'Waves', MilestoneStatus.notYet)],
        streak: 0,
        bestStreak: 0,
      );
      final words = [
        for (final b in summary.badges) ...[b.title, b.howTo],
      ].join(' ').toLowerCase();
      for (final banned in [
        'behind',
        'delay',
        'normal',
        'average',
        'other children',
      ]) {
        expect(words, isNot(contains(banned)));
      }
    });
  });

  group('day streak', () {
    test('counts consecutive days, keeping yesterday’s streak alive', () async {
      var now = DateTime(2026, 10, 1, 9);
      final prefs = MemoryPreferences();
      final e = EngagementState(prefs, clock: () => now);
      await e.checkIn();
      expect(e.streak, 1);
      now = DateTime(2026, 10, 2, 8);
      expect(e.streak, 1); // not checked yet today, still counts yesterday
      await e.checkIn();
      await e.checkIn(); // twice on one day counts once
      expect(e.streak, 2);
      now = DateTime(2026, 10, 4, 8); // a day missed
      expect(e.streak, 0);
      await e.checkIn();
      expect(e.streak, 1);
      expect(e.bestStreak, 2);

      final reloaded = EngagementState(prefs, clock: () => now);
      await reloaded.load();
      expect(reloaded.streak, 1);
      expect(reloaded.bestStreak, 2);

      await reloaded.clear();
      expect(reloaded.streak, 0);
      expect(prefs.values, isEmpty);
    });
  });

  test('theme mode is remembered on the device', () async {
    final prefs = MemoryPreferences();
    final theme = ThemeState(prefs);
    expect(theme.mode, ThemeMode.system);
    await theme.set(ThemeMode.dark);
    final again = ThemeState(prefs);
    await again.load();
    expect(again.mode, ThemeMode.dark);
  });

  group('home shell', () {
    FakeBackend backend({List<Map<String, dynamic>>? history}) => FakeBackend(
      (r) async {
        if (r.url.path.endsWith('/recommendations/')) {
          final id = r.url.pathSegments[2];
          return json(
            recs.batch([
              recs.card('ACT-$id', id == '3' ? 'Tummy Time' : 'Peekaboo'),
            ]),
          );
        }
        if (r.url.path.endsWith('/milestones/')) return json(history ?? []);
        if (r.url.path == '/api/reference-milestones/') return json([]);
        return json(caregiverJson);
      },
      children: [
        childJson(),
        childJson(id: 4, name: 'Zawadi', dob: '2025-02-01'),
      ],
    );

    testWidgets('opens on Today and checking ideas starts the streak', (
      tester,
    ) async {
      await pumpApp(tester, backend(), savedToken: 'tok');
      expect(find.text('From the village'), findsOneWidget);
      expect(find.text('Tummy Time'), findsOneWidget);
      final streak = find.byKey(const Key('streakChip'));
      expect(
        find.descendant(of: streak, matching: find.text('1')),
        findsOneWidget,
      );
    });

    testWidgets('the child switcher changes whose ideas are shown', (
      tester,
    ) async {
      final b = backend();
      await pumpApp(tester, b, savedToken: 'tok');
      await tapVisible(tester, find.byKey(const Key('childSwitcher')));
      await tapVisible(tester, find.byKey(const Key('switch_4')));
      expect(find.text('Peekaboo'), findsOneWidget);
      expect(b.to('/api/children/4/recommendations/'), isNotEmpty);
    });

    testWidgets('Progress shows celebrated milestones, areas and badges', (
      tester,
    ) async {
      await pumpApp(
        tester,
        backend(
          history: [
            obsJson('Language', 'Waves "bye-bye"', 'achieved'),
            obsJson('Motor', 'Walks alone', 'not_yet'),
          ],
        ),
        savedToken: 'tok',
      );
      await tapVisible(tester, find.byKey(const Key('tab_progress')));
      expect(find.text('1 milestone celebrated'), findsOneWidget);
      expect(find.byKey(const Key('area_Language')), findsOneWidget);
      expect(find.text('1 celebrated'), findsOneWidget);
      expect(find.text('0 celebrated · 1 practising'), findsOneWidget);
      await tester.scrollUntilVisible(
        find.byKey(const Key('badge_first_step')),
        200,
        scrollable: find.byType(Scrollable).last,
      );
      expect(find.text('First step'), findsOneWidget);
      expect(
        find.textContaining(RegExp('behind|delay', caseSensitive: false)),
        findsNothing,
      );
    });

    testWidgets('the theme picker switches the whole app to dark mode', (
      tester,
    ) async {
      final prefs = MemoryPreferences();
      await pumpApp(tester, backend(), savedToken: 'tok', preferences: prefs);
      expect(
        Theme.of(tester.element(find.byKey(const Key('tab_today')))).brightness,
        Brightness.light,
      );
      await tapVisible(tester, find.byKey(const Key('tab_family')));
      // Below the fold since the Account card (#138).
      await tester.scrollUntilVisible(
        find.byKey(const Key('toggle_Dark')),
        200,
        scrollable: find.byType(Scrollable).last,
      );
      await tapVisible(tester, find.byKey(const Key('toggle_Dark')));
      expect(
        Theme.of(tester.element(find.byKey(const Key('tab_today')))).brightness,
        Brightness.dark,
      );
      expect(prefs.values['nurtura.themeMode'], 'dark');
    });

    testWidgets('every tab renders in dark mode', (tester) async {
      await pumpApp(
        tester,
        backend(history: [obsJson('Language', 'Waves', 'achieved')]),
        savedToken: 'tok',
        preferences: MemoryPreferences({'nurtura.themeMode': 'dark'}),
      );
      for (final tab in [
        'tab_progress',
        'tab_milestones',
        'tab_family',
        'tab_today',
      ]) {
        await tapVisible(tester, find.byKey(Key(tab)));
        expect(tester.takeException(), isNull, reason: tab);
      }
      expect(
        Theme.of(tester.element(find.byKey(const Key('tab_today')))).brightness,
        Brightness.dark,
      );
    });
  });
}
