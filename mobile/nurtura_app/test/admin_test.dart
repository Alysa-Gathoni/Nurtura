import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/state/auth_state.dart';
import 'package:nurtura_app/state/preferences.dart';

import 'children_screen_test.dart' show tapVisible;
import 'helpers.dart';

const adminJson = {
  'id': 1,
  'username': 'lead@example.com',
  'email': 'lead@example.com',
  'first_name': '',
  'last_name': '',
  'role': 'administrator',
};

Map<String, dynamic> overviewJson({int range = 30, bool indexStale = false}) {
  final days = List.generate(
    range,
    (i) => DateTime(2026, 10, 21).subtract(Duration(days: range - 1 - i)),
  );
  List<int> zeros(int n, [int last = 0]) => [...List.filled(n - 1, 0), last];
  return {
    'range': range,
    'ranges': [7, 30, 90],
    'people': {
      'caregivers': 12,
      'active_caregivers': 5,
      'active_days': 7,
      'children': 15,
      'children_born': 13,
      'children_expecting': 2,
    },
    'trend': {
      'dates': [
        for (final d in days)
          '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}',
      ],
      'series': {
        'ideas': zeros(range, 4),
        'milestones': zeros(range, 3),
        'feedback': zeros(range, 2),
      },
      'totals': {'ideas': 4, 'milestones': 3, 'feedback': 2, 'signups': 1},
    },
    'spark': {
      'days': 14,
      'series': {
        'signups': zeros(14, 1),
        'ideas': zeros(14, 4),
        'milestones': zeros(14, 3),
        'feedback': zeros(14, 2),
      },
      'totals': {'signups': 1, 'ideas': 4, 'milestones': 3, 'feedback': 2},
    },
    'outcomes': {
      'recommended': 20,
      'done': 6,
      'partly': 2,
      'not_marked': 12,
      'tried_share': 40,
    },
    'ratings': {
      'count': 4,
      'average': 3.5,
      'by_star': [0, 1, 1, 1, 1],
    },
    'milestones': {
      'total': 9,
      'by_status': [
        {'status': 'achieved', 'label': 'Achieved', 'count': 5},
        {'status': 'emerging', 'label': 'Emerging', 'count': 1},
        {'status': 'not_yet', 'label': 'Not yet', 'count': 3},
      ],
    },
    'needs_attention': [
      {
        'pk': 3,
        'activity_id': 'ACT-0003',
        'name': 'Block Tower',
        'average': 2.0,
        'ratings': 1,
      },
    ],
    'needs_attention_at': 2.5,
    'health': [
      {
        'status': 'good',
        'title': 'AI model ready',
        'detail': 'all-MiniLM-L6-v2 is installed',
      },
      indexStale
          ? {
              'status': 'warning',
              'title': 'Search index out of date',
              'detail': '1 Published activity not searchable yet',
            }
          : {
              'status': 'good',
              'title': 'Search index up to date',
              'detail': 'Every Published activity is searchable',
            },
    ],
    'waiting': {
      'drafts': 1,
      'under_review': 2,
      'unverified': 108,
      'milestones_total': 133,
      'verified_share': 19,
    },
    'coverage': {
      'ages': ['0–3', '3–6', '6–12', '12–18', '18–24', '24–36'],
      'rows': [
        for (final d in [
          'Cognitive',
          'Language',
          'Motor',
          'Sensory',
          'Socio-Emotional',
        ])
          {
            'label': d,
            'cells': [
              for (var i = 0; i < 6; i++)
                {
                  'age': '$i',
                  'count': d == 'Sensory' && i == 4 ? 0 : 2,
                  'level': 2,
                },
            ],
          },
      ],
      'gaps': 1,
      'prenatal': 8,
    },
    'events': [
      {
        'when': '2026-10-21T08:00:00Z',
        'kind': 'feedback',
        'title': 'Rated 5★',
        'detail': 'Peekaboo',
      },
    ],
    'most_recommended': [
      {
        'pk': 1,
        'activity_id': 'ACT-0001',
        'name': 'Peekaboo',
        'domain': 'Socio-Emotional',
        'times': 6,
        'done_share': 50,
        'average': 4.5,
        'status': 'Published',
        'status_key': 'published',
      },
    ],
  };
}

Map<String, dynamic> activityJson({
  int id = 1,
  String code = 'ACT-0001',
  String name = 'Peekaboo',
  String status = 'published',
  String domain = 'Socio-Emotional',
}) => {
  'id': id,
  'activity_id': code,
  'activity_name': name,
  'developmental_domain': domain,
  'age_range': '6-12 months',
  'developmental_goal': 'Object permanence and turn-taking',
  'materials': 'A cloth',
  'difficulty_level': 'Beginner',
  'description': 'Hide your face, then appear.',
  'cultural_relevance': 'Any cloth will do.',
  'plain_aim': 'help your baby learn that people come back',
  'source': 'CDC',
  'source_url': '',
  'content_status': status,
  'status_label': {
    'draft': 'Draft',
    'under_review': 'Under Review',
    'published': 'Published',
  }[status],
  'times_recommended': 6,
  'feedback_count': 2,
  'average_rating': 4.5,
  'searchable': status == 'published',
  'updated_at': '2026-10-20T10:00:00Z',
};

const choicesJson = {
  'domains': [
    {'value': 'Cognitive', 'label': 'Cognitive'},
    {'value': 'Language', 'label': 'Language'},
    {'value': 'Motor', 'label': 'Motor'},
    {'value': 'Sensory', 'label': 'Sensory'},
    {'value': 'Socio-Emotional', 'label': 'Socio-Emotional'},
  ],
  'age_ranges': [
    {'value': '6-12 months', 'label': '6-12 months'},
    {'value': '12-18 months', 'label': '12-18 months'},
  ],
  'difficulty_levels': [
    {'value': 'Beginner', 'label': 'Beginner'},
  ],
  'sources': [
    {'value': 'CDC', 'label': 'CDC'},
    {'value': 'UNICEF', 'label': 'UNICEF'},
  ],
  'statuses': [
    {'value': 'draft', 'label': 'Draft'},
    {'value': 'under_review', 'label': 'Under Review'},
    {'value': 'published', 'label': 'Published'},
  ],
  'transitions': {
    'draft': ['under_review'],
    'under_review': ['draft', 'published'],
    'published': ['draft'],
  },
};

Map<String, dynamic> feedbackJson(int id, int rating) => {
  'id': id,
  'rating': rating,
  'comment': 'Comment $id',
  'date_submitted': '2026-10-2${id % 10}T09:00:00Z',
  'completion': id.isEven ? 'completed' : null,
  'activity': {
    'id': 1,
    'activity_id': 'ACT-0001',
    'name': 'Peekaboo',
    'domain': 'Socio-Emotional',
    'age_range': '6-12 months',
  },
};

/// A fake admin API; [handler] can override any route.
FakeBackend adminBackend({
  bool indexStale = false,
  List<Map<String, dynamic>>? activities,
  Future<http.Response?> Function(http.Request)? handler,
  int feedbackTotal = 3,
}) {
  return FakeBackend((r) async {
    final custom = await handler?.call(r);
    if (custom != null) return custom;
    final path = r.url.path;
    if (path == '/api/auth/me/') return json(adminJson);
    if (path == '/api/admin/overview/') {
      return json(
        overviewJson(
          range: int.parse(r.url.queryParameters['range'] ?? '30'),
          indexStale: indexStale,
        ),
      );
    }
    if (path == '/api/admin/choices/') return json(choicesJson);
    if (path == '/api/admin/activities/' && r.method == 'GET') {
      return json(
        activities ??
            [
              activityJson(),
              activityJson(
                id: 2,
                code: 'ACT-0002',
                name: 'Clapping Songs',
                status: 'draft',
                domain: 'Language',
              ),
            ],
      );
    }
    if (path == '/api/admin/feedback/') {
      final offset = int.parse(r.url.queryParameters['offset'] ?? '0');
      final limit = int.parse(r.url.queryParameters['limit'] ?? '30');
      final all = [
        for (var i = 1; i <= feedbackTotal; i++) feedbackJson(i, 1 + i % 5),
      ];
      return json({
        'count': all.length,
        'results': all.skip(offset).take(limit).toList(),
      });
    }
    if (path == '/api/admin/search-index/') {
      return json({
        'message': '1 Published: 1 embedded, 0 up to date, 0 removed (no longer Published)',
        'not_searchable': 0,
      });
    }
    if (path == '/api/auth/logout/') return http.Response('', 204);
    return http.Response('', 404);
  }, serveChildren: false);
}

Future<MemoryPreferences> pumpAdmin(
  WidgetTester tester,
  FakeBackend backend, {
  MemoryPreferences? prefs,
}) async {
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 2.6;
  addTearDown(tester.view.reset);
  final preferences = prefs ?? MemoryPreferences();
  await pumpApp(tester, backend, savedToken: 'tok', preferences: preferences);
  return preferences;
}

/// Scrolls the first scrollable (lazy lists build only what is near the
/// screen) until [finder] is built and visible.
Future<void> scrollTo(
  WidgetTester tester,
  Finder finder, {
  double delta = 300,
}) => tester.scrollUntilVisible(
  finder,
  delta,
  scrollable: find.byType(Scrollable).first,
);

Finder get _form => find
    .descendant(
      of: find.byKey(const Key('activityForm')),
      matching: find.byType(Scrollable),
    )
    .first;

/// Scrolls the activity form from the top until [finder] is visible.
Future<void> _reachInForm(WidgetTester tester, Finder finder) async {
  tester.state<ScrollableState>(_form).position.jumpTo(0);
  await tester.pump();
  await tester.scrollUntilVisible(finder, 200, scrollable: _form);
}

Future<void> tapInForm(WidgetTester tester, Finder finder) async {
  await _reachInForm(tester, finder);
  await tapVisible(tester, finder);
}

Future<void> typeInForm(WidgetTester tester, String key, String text) async {
  final finder = find.byKey(Key(key));
  await _reachInForm(tester, finder);
  await tester.enterText(finder, text);
}

void main() {
  group('routing by role', () {
    testWidgets('an administrator lands on the admin dashboard', (
      tester,
    ) async {
      final prefs = await pumpAdmin(tester, adminBackend());
      expect(find.byKey(const Key('adminBadge')), findsOneWidget);
      expect(find.byKey(const Key('admin_tab_dashboard')), findsOneWidget);
      expect(find.byKey(const Key('tab_today')), findsNothing);
      expect(find.byKey(const Key('overviewCard')), findsOneWidget);
      expect(prefs.values[AuthState.roleKey], 'administrator');
    });

    testWidgets('opened offline, an administrator still gets admin screens', (
      tester,
    ) async {
      await pumpAdmin(
        tester,
        FakeBackend(
          (r) async => throw http.ClientException('offline'),
          serveChildren: false,
        ),
        prefs: MemoryPreferences({AuthState.roleKey: 'administrator'}),
      );
      expect(find.byKey(const Key('adminBadge')), findsOneWidget);
      expect(find.byKey(const Key('dashboardError')), findsOneWidget);
    });

    testWidgets('logging out forgets the role', (tester) async {
      final prefs = await pumpAdmin(tester, adminBackend());
      await tapVisible(tester, find.byKey(const Key('admin_tab_account')));
      expect(find.text('lead@example.com'), findsOneWidget);
      await tapVisible(tester, find.byKey(const Key('logoutButton')));
      expect(find.byKey(const Key('emailField')), findsOneWidget);
      expect(prefs.values.containsKey(AuthState.roleKey), isFalse);
    });
  });

  group('dashboard', () {
    testWidgets('shows use, outcomes, health, work and coverage', (
      tester,
    ) async {
      await pumpAdmin(tester, adminBackend());
      expect(find.text('4'), findsWidgets); // idea batches
      expect(find.textContaining('5 active this week'), findsOneWidget);
      expect(find.byKey(const Key('trendChart')), findsOneWidget);
      expect(find.text('40%'), findsWidgets); // tried share
      await scrollTo(tester, find.byKey(const Key('stat_signups')));
      await scrollTo(tester, find.text('AI model ready'));
      await scrollTo(tester, find.text('108')); // milestones to verify
      await scrollTo(tester, find.byKey(const Key('coverageCard')));
      expect(find.byKey(const Key('updateIndexButton')), findsNothing);
    });

    testWidgets('the range tabs ask for a different period', (tester) async {
      final backend = adminBackend();
      await pumpAdmin(tester, backend);
      await tapVisible(tester, find.text('7 days'));
      expect(
        backend.to('/api/admin/overview/').last.url.queryParameters['range'],
        '7',
      );
      expect(find.text('The last 7 days'), findsOneWidget);
    });

    testWidgets('the trend chart shows a day on touch', (tester) async {
      await pumpAdmin(tester, adminBackend());
      final chart = find.byKey(const Key('trendChart'));
      await tester.tapAt(tester.getBottomRight(chart) - const Offset(4, 30));
      await tester.pump();
      expect(find.byKey(const Key('trendTooltip')), findsOneWidget);
    });

    testWidgets('an out-of-date search index can be updated from the phone', (
      tester,
    ) async {
      final backend = adminBackend(indexStale: true);
      await pumpAdmin(tester, backend);
      await scrollTo(tester, find.byKey(const Key('updateIndexButton')));
      await tapVisible(tester, find.byKey(const Key('updateIndexButton')));
      expect(backend.to('/api/admin/search-index/').single.method, 'POST');
      expect(find.textContaining('1 embedded'), findsOneWidget);
    });

    testWidgets('"Activities to review" opens the filtered Activities tab', (
      tester,
    ) async {
      final backend = adminBackend();
      await pumpAdmin(tester, backend);
      await scrollTo(tester, find.byKey(const Key('workReview')));
      await tapVisible(tester, find.byKey(const Key('workReview')));
      expect(find.byKey(const Key('adminActivities')), findsOneWidget);
      expect(
        backend.to('/api/admin/activities/').last.url.queryParameters['status'],
        'under_review',
      );
    });
  });

  group('activities', () {
    Future<FakeBackend> openActivities(
      WidgetTester tester, {
      Future<http.Response?> Function(http.Request)? handler,
    }) async {
      final backend = adminBackend(handler: handler);
      await pumpAdmin(tester, backend);
      await tapVisible(tester, find.byKey(const Key('admin_tab_activities')));
      return backend;
    }

    testWidgets('lists activities and filters them', (tester) async {
      final backend = await openActivities(tester);
      expect(find.byKey(const Key('activity_ACT-0001')), findsOneWidget);
      expect(find.byKey(const Key('activity_ACT-0002')), findsOneWidget);
      expect(find.text('2 activities'), findsOneWidget);
      await tapVisible(tester, find.byKey(const Key('status_draft')));
      expect(
        backend.to('/api/admin/activities/').last.url.queryParameters['status'],
        'draft',
      );
      await tapVisible(tester, find.byKey(const Key('area_Language')));
      expect(
        backend.to('/api/admin/activities/').last.url.queryParameters['domain'],
        'Language',
      );
      await tester.enterText(find.byKey(const Key('activitySearch')), 'clap');
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pumpAndSettle();
      expect(
        backend.to('/api/admin/activities/').last.url.queryParameters['search'],
        'clap',
      );
    });

    testWidgets('adds an activity as a draft', (tester) async {
      final backend = await openActivities(
        tester,
        handler: (r) async =>
            r.method == 'POST' && r.url.path == '/api/admin/activities/'
            ? json(
                activityJson(
                  id: 9,
                  code: 'ACT-0055',
                  name: 'Clapping Songs',
                  status: 'draft',
                  domain: 'Language',
                ),
                201,
              )
            : null,
      );
      await tapVisible(tester, find.byKey(const Key('addActivityButton')));
      await tapInForm(tester, find.byKey(const Key('saveActivityButton')));
      expect(find.text('Required.'), findsWidgets); // nothing sent yet
      expect(backend.requests.where((r) => r.method == 'POST'), isEmpty);

      await typeInForm(tester, 'field_activity_name', 'Clapping Songs');
      for (final (key, value) in [
        ('developmental_domain', 'Language'),
        ('age_range', '6-12 months'),
        ('difficulty_level', 'Beginner'),
        ('source', 'UNICEF'),
      ]) {
        await tapInForm(tester, find.byKey(Key('field_$key')));
        await tester.tap(find.text(value).last);
        await tester.pumpAndSettle();
      }
      await typeInForm(tester, 'field_developmental_goal', 'Rhythm');
      await typeInForm(tester, 'field_materials', 'None');
      await typeInForm(tester, 'field_description', 'Clap and sing.');
      await typeInForm(tester, 'field_cultural_relevance', 'Local songs.');
      await tapInForm(tester, find.byKey(const Key('saveActivityButton')));

      final sent = jsonDecode(
        backend.requests.lastWhere((r) => r.method == 'POST').body,
      ) as Map;
      expect(sent['activity_name'], 'Clapping Songs');
      expect(sent['developmental_domain'], 'Language');
      expect(sent.containsKey('content_status'), isFalse);
      expect(find.text('Added as ACT-0055, in Draft.'), findsOneWidget);
    });

    testWidgets('server field errors appear under the field', (tester) async {
      await openActivities(
        tester,
        handler: (r) async => r.method == 'PATCH'
            ? json({
                'plain_aim': ['Start with a lower-case letter.'],
              }, 400)
            : null,
      );
      await tapVisible(tester, find.byKey(const Key('activity_ACT-0001')));
      await tapInForm(tester, find.byKey(const Key('saveActivityButton')));
      expect(find.byKey(const Key('formError')), findsOneWidget);
      await _reachInForm(tester, find.text('Start with a lower-case letter.'));
    });

    testWidgets('editing a published activity says it went back to Draft', (
      tester,
    ) async {
      final backend = await openActivities(
        tester,
        handler: (r) async => r.method == 'PATCH'
            ? json(activityJson(status: 'draft', name: 'Peekaboo Plus'))
            : null,
      );
      await tapVisible(tester, find.byKey(const Key('activity_ACT-0001')));
      expect(
        find.textContaining('sends this activity back to Draft'),
        findsOneWidget,
      );
      await typeInForm(tester, 'field_activity_name', 'Peekaboo Plus');
      await tapInForm(tester, find.byKey(const Key('saveActivityButton')));
      expect(backend.requests.last.method, 'PATCH');
      expect(find.textContaining('went back to Draft'), findsOneWidget);
    });

    testWidgets('moves through review, confirming before unpublishing', (
      tester,
    ) async {
      final backend = await openActivities(
        tester,
        handler: (r) async => r.url.path.endsWith('/status/')
            ? json(
                activityJson(
                  status: (jsonDecode(r.body) as Map)['status'] as String,
                ),
              )
            : null,
      );
      await tapVisible(tester, find.byKey(const Key('activity_ACT-0001')));
      await tapVisible(tester, find.byKey(const Key('move_draft')));
      expect(find.text('Unpublish this activity?'), findsOneWidget);
      await tapVisible(tester, find.text('Cancel'));
      expect(backend.to('/api/admin/activities/1/status/'), isEmpty);

      await tapVisible(tester, find.byKey(const Key('move_draft')));
      await tapVisible(tester, find.byKey(const Key('confirmUnpublish')));
      expect(
        jsonDecode(backend.to('/api/admin/activities/1/status/').single.body),
        {'status': 'draft'},
      );
      expect(find.text('Now Draft.'), findsOneWidget);
      await tapVisible(tester, find.byKey(const Key('move_under_review')));
      expect(find.byKey(const Key('move_published')), findsOneWidget);
      await tapVisible(tester, find.byKey(const Key('move_published')));
      expect(find.textContaining('Update the search index'), findsOneWidget);
    });
  });

  group('feedback', () {
    testWidgets('lists feedback against activities, filters and pages', (
      tester,
    ) async {
      final backend = adminBackend(feedbackTotal: 35);
      await pumpAdmin(tester, backend);
      await tapVisible(tester, find.byKey(const Key('admin_tab_feedback')));
      expect(find.text('35 ratings'), findsOneWidget);
      expect(find.text('“Comment 1”'), findsOneWidget);
      expect(find.textContaining('Peekaboo'), findsWidgets);
      await scrollTo(tester, find.byKey(const Key('moreFeedback')));
      await tapVisible(tester, find.byKey(const Key('moreFeedback')));
      expect(
        backend.to('/api/admin/feedback/').last.url.queryParameters['offset'],
        '30',
      );
      expect(find.byKey(const Key('moreFeedback')), findsNothing);
      await scrollTo(tester, find.byKey(const Key('rating_5')), delta: -400);
      await tapVisible(tester, find.byKey(const Key('rating_5')));
      expect(
        backend.to('/api/admin/feedback/').last.url.queryParameters['rating'],
        '5',
      );
    });
  });
}
