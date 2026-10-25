import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/models/recommendation.dart';
import 'package:nurtura_app/state/recommendation_cache.dart';
import 'package:nurtura_app/utils/dates.dart' as dates;

import 'helpers.dart';

// Editing and deleting a child, and deleting the account (#134).

Map<String, dynamic> childJson({
  int id = 3,
  String name = 'Amani',
  String dob = '2025-08-01',
  List<String> interests = const [],
  List<String> concerns = const [],
}) => {
  'id': id,
  'name': name,
  'date_of_birth': dob,
  'gender': 'unspecified',
  'interests': interests,
  'preferences': {},
  'concerns': concerns,
  'created_at': '2026-10-01T08:00:00Z',
  'updated_at': '2026-10-01T08:00:00Z',
};

const emptyBatch = {'batch': null, 'generated_at': null, 'recommendations': []};

/// A stored batch with one idea, so opening Today doesn't generate one.
const storedBatch = {
  'batch': 'b-1',
  'generated_at': '2026-10-01T08:00:00Z',
  'recommendations': [
    {
      'id': 1,
      'batch': 'b-1',
      'position': 1,
      'generated_at': '2026-10-01T08:00:00Z',
      'activity_id': 'ACT-0001',
      'activity_name': 'Tummy Time',
      'developmental_domain': 'Motor',
      'age_range': '12-18 months',
      'short_description': 'Time on the tummy.',
      'explanation': 'It suits your child.',
    },
  ],
};

Map<String, dynamic>? body(http.Request r) =>
    r.body.isEmpty ? null : jsonDecode(r.body) as Map<String, dynamic>;

Future<void> tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

/// A backend that answers `/me`, recommendations, and the [extra] routes.
FakeBackend backendWith(
  Future<http.Response?> Function(http.Request r) extra, {
  List<Map<String, dynamic>> children = const [],
}) => FakeBackend((r) async {
  final answer = await extra(r);
  if (answer != null) return answer;
  if (r.url.path == '/api/auth/me/') return json(caregiverJson);
  if (r.url.path.endsWith('/recommendations/')) {
    return json(storedBatch);
  }
  return json({'detail': 'Not found.'}, 404);
}, children: children);

Future<void> openFamily(WidgetTester tester) =>
    tapVisible(tester, find.byKey(const Key('tab_family')));

/// The Family tab's "Delete account" sits below the fold.
Future<void> openDeleteAccount(WidgetTester tester) async {
  final button = find.byKey(const Key('deleteAccountButton'));
  await tester.scrollUntilVisible(
    button,
    200,
    scrollable: find.byType(Scrollable).last,
  );
  await tapVisible(tester, button);
}

void main() {
  setUpAll(() => WidgetController.hitTestWarningShouldBeFatal = true);
  setUp(() => dates.clock = () => DateTime(2026, 10, 1, 9));
  tearDown(() => dates.clock = DateTime.now);

  group('edit a child', () {
    testWidgets('the form opens filled in and saves the changes', (
      tester,
    ) async {
      final backend = backendWith(
        (r) async {
          if (r.method == 'PATCH' && r.url.path == '/api/children/3/') {
            final b = body(r)!;
            return json(
              childJson(
                name: b['name'] as String,
                interests: List<String>.from(b['interests'] as List),
                concerns: List<String>.from(b['concerns'] as List),
              ),
            );
          }
          return null;
        },
        children: [
          childJson(interests: ['music']),
        ],
      );
      await pumpApp(tester, backend, savedToken: 'tok');
      await openFamily(tester);

      await tapVisible(tester, find.byKey(const Key('editChild_3')));
      expect(find.text('Edit profile'), findsOneWidget);
      expect(find.widgetWithText(TextField, 'Amani'), findsOneWidget);
      expect(find.text('1 Aug 2025'), findsOneWidget);
      expect(find.byKey(const Key('interest_music')), findsOneWidget);

      await tester.enterText(find.byKey(const Key('childNameField')), 'Zawadi');
      await tapVisible(tester, find.byKey(const Key('concern_Language')));
      await tapVisible(tester, find.byKey(const Key('saveChildButton')));

      final patch = backend.to('/api/children/3/').single;
      expect(body(patch), {
        'name': 'Zawadi',
        'date_of_birth': '2025-08-01',
        'interests': ['music'],
        'concerns': ['Language'],
      });
      expect(find.text('Edit profile'), findsNothing);
      expect(find.text('Zawadi'), findsOneWidget);
      expect(find.text('Language'), findsOneWidget);
    });

    testWidgets('after an edit, Today asks for fresh ideas once', (
      tester,
    ) async {
      final backend = backendWith((r) async {
        if (r.method == 'PATCH') return json(childJson(interests: ['books']));
        return null;
      }, children: [childJson()]);
      await pumpApp(tester, backend, savedToken: 'tok');
      const ideas = '/api/children/3/recommendations/';
      int posts() => backend.to(ideas).where((r) => r.method == 'POST').length;
      final before = posts();

      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('editChild_3')));
      await tapVisible(tester, find.byKey(const Key('saveChildButton')));
      await tapVisible(tester, find.byKey(const Key('tab_today')));
      expect(posts(), before + 1);

      // Back and forth without an edit: the stored batch is shown again.
      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('tab_today')));
      expect(posts(), before + 1);
    });

    testWidgets('a refused change is shown and nothing changes', (
      tester,
    ) async {
      final backend = backendWith((r) async {
        if (r.method == 'PATCH') {
          return json({
            'date_of_birth': ['Too far in the future.'],
          }, 400);
        }
        return null;
      }, children: [childJson()]);
      await pumpApp(tester, backend, savedToken: 'tok');
      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('editChild_3')));
      await tapVisible(tester, find.byKey(const Key('saveChildButton')));

      expect(find.text('Too far in the future.'), findsOneWidget);
      expect(find.text('Edit profile'), findsOneWidget);
    });
  });

  group('delete a child', () {
    testWidgets('after confirming, the profile and its saved ideas go', (
      tester,
    ) async {
      final cache = MemoryRecommendationCache();
      final saved = RecommendationBatch.fromJson(emptyBatch);
      await cache.write(3, saved);
      await cache.write(4, saved);
      final backend = backendWith(
        (r) async => r.method == 'DELETE' ? http.Response('', 204) : null,
        children: [
          childJson(),
          childJson(id: 4, name: 'Baraka'),
        ],
      );
      await pumpApp(tester, backend, savedToken: 'tok', cache: cache);
      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('editChild_3')));

      // Cancelling keeps everything.
      await tapVisible(tester, find.byKey(const Key('deleteChildButton')));
      expect(find.text("Delete Amani's profile?"), findsOneWidget);
      await tapVisible(tester, find.text('Cancel'));
      expect(backend.requests.where((r) => r.method == 'DELETE'), isEmpty);

      await tapVisible(tester, find.byKey(const Key('deleteChildButton')));
      await tapVisible(tester, find.byKey(const Key('confirmDeleteChild')));

      expect(
        backend.requests.where((r) => r.method == 'DELETE').single.url.path,
        '/api/children/3/',
      );
      expect(find.text("Amani's profile was deleted."), findsOneWidget);
      expect(find.text('Amani'), findsNothing);
      expect(find.text('Baraka'), findsWidgets);
      expect(cache.entries.keys, [4]);
    });

    testWidgets('deleting the last child goes back to "Add your first child"', (
      tester,
    ) async {
      final backend = backendWith(
        (r) async => r.method == 'DELETE' ? http.Response('', 204) : null,
        children: [childJson()],
      );
      await pumpApp(tester, backend, savedToken: 'tok');
      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('editChild_3')));
      await tapVisible(tester, find.byKey(const Key('deleteChildButton')));
      await tapVisible(tester, find.byKey(const Key('confirmDeleteChild')));

      expect(find.text('Add your first child'), findsOneWidget);
    });

    testWidgets('a failed delete keeps the child and says why', (tester) async {
      final backend = backendWith(
        (r) async => r.method == 'DELETE'
            ? json({'detail': 'Something went wrong.'}, 500)
            : null,
        children: [childJson()],
      );
      await pumpApp(tester, backend, savedToken: 'tok');
      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('editChild_3')));
      await tapVisible(tester, find.byKey(const Key('deleteChildButton')));
      await tapVisible(tester, find.byKey(const Key('confirmDeleteChild')));

      expect(find.byKey(const Key('childError')), findsOneWidget);
      expect(find.text('Edit profile'), findsOneWidget);
    });
  });

  group('delete the account', () {
    Future<void> confirmWith(WidgetTester tester, String value) async {
      await tester.enterText(
        find.byKey(const Key('deleteAccountField')),
        value,
      );
      await tapVisible(tester, find.byKey(const Key('confirmDeleteAccount')));
    }

    testWidgets('with the password: signs out and forgets saved data', (
      tester,
    ) async {
      final cache = MemoryRecommendationCache();
      await cache.write(3, RecommendationBatch.fromJson(emptyBatch));
      final backend = backendWith((r) async {
        if (r.method == 'DELETE' && r.url.path == '/api/auth/me/') {
          return http.Response('', 204);
        }
        return null;
      }, children: [childJson()]);
      final store = await pumpApp(
        tester,
        backend,
        savedToken: 'tok',
        cache: cache,
      );
      await openFamily(tester);
      await openDeleteAccount(tester);
      expect(find.text('Delete your account?'), findsOneWidget);

      // Nothing typed: asked for the password, nothing sent.
      await tapVisible(tester, find.byKey(const Key('confirmDeleteAccount')));
      expect(find.text('Type your password.'), findsOneWidget);
      expect(backend.requests.where((r) => r.method == 'DELETE'), isEmpty);

      await confirmWith(tester, 'Str0ng-Passw0rd!');
      final delete = backend.requests.where((r) => r.method == 'DELETE').single;
      expect(delete.url.path, '/api/auth/me/');
      expect(body(delete), {'password': 'Str0ng-Passw0rd!'});
      expect(find.byKey(const Key('submitButton')), findsOneWidget);
      expect(store.token, isNull);
      expect(cache.entries, isEmpty);
    });

    testWidgets('a wrong password is shown and nothing is forgotten', (
      tester,
    ) async {
      final backend = backendWith((r) async {
        if (r.method == 'DELETE') {
          return json({
            'password': ["That password isn't right."],
          }, 400);
        }
        return null;
      }, children: [childJson()]);
      final store = await pumpApp(tester, backend, savedToken: 'tok');
      await openFamily(tester);
      await openDeleteAccount(tester);
      await confirmWith(tester, 'wrong');

      expect(find.text("That password isn't right."), findsOneWidget);
      expect(store.token, 'tok');
      await tapVisible(tester, find.text('Cancel'));
      expect(find.text('Amani'), findsWidgets);
    });

    testWidgets('an account with no password confirms with its email', (
      tester,
    ) async {
      final backend = backendWith((r) async {
        if (r.method != 'DELETE') return null;
        if (body(r)!.containsKey('email')) return http.Response('', 204);
        return json({
          'email': ['Type the email address of this account.'],
        }, 400);
      }, children: [childJson()]);
      final store = await pumpApp(tester, backend, savedToken: 'tok');
      await openFamily(tester);
      await openDeleteAccount(tester);
      await confirmWith(tester, 'anything');

      expect(find.text('Your email'), findsOneWidget);
      await confirmWith(tester, ' wanjiru@example.com ');
      final deletes = backend.requests.where((r) => r.method == 'DELETE');
      expect(body(deletes.last), {'email': 'wanjiru@example.com'});
      expect(store.token, isNull);
    });

    testWidgets('a caregiver with no children can delete the account too', (
      tester,
    ) async {
      final backend = backendWith(
        (r) async => r.method == 'DELETE' ? http.Response('', 204) : null,
      );
      final store = await pumpApp(tester, backend, savedToken: 'tok');
      expect(find.text('Add your first child'), findsOneWidget);
      await tapVisible(tester, find.byKey(const Key('accountMenu')));
      await tapVisible(tester, find.byKey(const Key('deleteAccountButton')));
      await confirmWith(tester, 'Str0ng-Passw0rd!');

      expect(store.token, isNull);
      expect(find.byKey(const Key('submitButton')), findsOneWidget);
    });
  });
}
