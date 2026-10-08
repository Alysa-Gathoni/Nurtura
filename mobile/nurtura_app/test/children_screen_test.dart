import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/utils/dates.dart' as dates;

import 'helpers.dart';

Future<void> tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

Map<String, dynamic> childJson({
  int id = 3,
  String name = 'Amani',
  String dob = '2025-08-01',
  List<String> interests = const [],
  List<String> concerns = const [],
}) =>
    {
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

void main() {
  setUpAll(() => WidgetController.hitTestWarningShouldBeFatal = true);
  setUp(() => dates.clock = () => DateTime(2026, 10, 1, 9));
  tearDown(() => dates.clock = DateTime.now);

  testWidgets('a new caregiver sees an empty state', (tester) async {
    await pumpApp(
      tester,
      FakeBackend((_) async => json(caregiverJson)),
      savedToken: 'tok',
    );
    expect(find.text('Add your first child'), findsOneWidget);
  });

  testWidgets('lists children with age, due date and concerns', (tester) async {
    await pumpApp(
      tester,
      FakeBackend(
        (_) async => json(caregiverJson),
        children: [
          childJson(concerns: ['Language']),
          childJson(id: 4, name: 'Baby', dob: '2027-02-01'),
        ],
      ),
      savedToken: 'tok',
    );
    expect(find.text('Amani'), findsOneWidget);
    expect(find.text('14 months'), findsOneWidget);
    expect(find.text('Language'), findsOneWidget);
    expect(find.text('Due 1 Feb 2027'), findsOneWidget);
    expect(find.text('Expecting'), findsOneWidget);
  });

  testWidgets('a failed load shows the error and can be retried',
      (tester) async {
    var childrenCalls = 0;
    await pumpApp(
      tester,
      FakeBackend(
        (request) async {
          if (request.url.path == '/api/children/') {
            childrenCalls++;
            return childrenCalls == 1
                ? json({'detail': 'Server error'}, 500)
                : json([childJson()]);
          }
          return json(caregiverJson);
        },
        serveChildren: false,
      ),
      savedToken: 'tok',
    );
    expect(
      find.text('The server had a problem (500). Please try again shortly.'),
      findsOneWidget,
    );
    await tapVisible(tester, find.byKey(const Key('retryButton')));
    expect(find.text('Amani'), findsOneWidget);
  });

  testWidgets('creates an expecting (prenatal) profile with interests and '
      'concerns', (tester) async {
    late Map<String, dynamic> sent;
    final backend = FakeBackend((request) async {
      if (request.method == 'POST' && request.url.path == '/api/children/') {
        sent = jsonDecode(request.body) as Map<String, dynamic>;
        return json(
          childJson(
            name: sent['name'] as String,
            dob: sent['date_of_birth'] as String,
            interests: List<String>.from(sent['interests'] as List),
            concerns: List<String>.from(sent['concerns'] as List),
          ),
          201,
        );
      }
      return json(caregiverJson);
    });
    await pumpApp(tester, backend, savedToken: 'tok');

    await tapVisible(tester, find.byKey(const Key('addChildButton')));
    await tester.enterText(find.byKey(const Key('childNameField')).last, 'Amani');
    await tapVisible(tester, find.byKey(const Key('toggle_Expecting')));
    await tapVisible(tester, find.byKey(const Key('dateField')));
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
    expect(find.text('30 Dec 2026'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('interestField')).last, 'water play');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('interest_water play')), findsOneWidget);
    await tapVisible(tester, find.byKey(const Key('concern_Sensory')));
    await tapVisible(tester, find.byKey(const Key('saveChildButton')));

    expect(sent, {
      'name': 'Amani',
      'date_of_birth': '2026-12-30',
      'interests': ['water play'],
      'concerns': ['Sensory'],
    });
    expect(find.text('Your children'), findsOneWidget);
    expect(find.text("Amani's profile is saved."), findsOneWidget);
    expect(find.text('Due 30 Dec 2026'), findsOneWidget);
  });

  testWidgets('requires a name and a date before sending anything',
      (tester) async {
    final backend = FakeBackend((_) async => json(caregiverJson));
    await pumpApp(tester, backend, savedToken: 'tok');
    await tapVisible(tester, find.byKey(const Key('addChildButton')));
    await tapVisible(tester, find.byKey(const Key('saveChildButton')));

    expect(find.text("Enter your child's name."), findsOneWidget);
    expect(find.text('Choose the date of birth.'), findsOneWidget);
    expect(backend.requests.where((r) => r.method == 'POST'), isEmpty);
  });

  testWidgets('switching between born and expecting clears the date',
      (tester) async {
    await pumpApp(
      tester,
      FakeBackend((_) async => json(caregiverJson)),
      savedToken: 'tok',
    );
    await tapVisible(tester, find.byKey(const Key('addChildButton')));
    await tapVisible(tester, find.byKey(const Key('dateField')));
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
    expect(find.text('1 Apr 2026'), findsOneWidget);

    await tapVisible(tester, find.byKey(const Key('toggle_Expecting')));
    expect(find.text('1 Apr 2026'), findsNothing);
    expect(find.text('Expected due date'), findsOneWidget);
  });

  testWidgets('backend validation errors appear next to the field',
      (tester) async {
    await pumpApp(
      tester,
      FakeBackend((request) async {
        if (request.method == 'POST') {
          return json({
            'concerns': ["Unknown domain(s): ['Visual']."],
          }, 400);
        }
        return json(caregiverJson);
      }),
      savedToken: 'tok',
    );
    await tapVisible(tester, find.byKey(const Key('addChildButton')));
    await tester.enterText(find.byKey(const Key('childNameField')).last, 'Amani');
    await tapVisible(tester, find.byKey(const Key('dateField')));
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
    await tapVisible(tester, find.byKey(const Key('saveChildButton')));

    expect(find.text("Unknown domain(s): ['Visual']."), findsOneWidget);
    expect(find.text('Add a child'), findsWidgets);
  });

  testWidgets('logging out clears the children list', (tester) async {
    await pumpApp(
      tester,
      FakeBackend(
        (request) async => request.url.path == '/api/auth/logout/'
            ? http.Response('', 204)
            : json(caregiverJson),
        children: [childJson()],
      ),
      savedToken: 'tok',
    );
    expect(find.text('Amani'), findsOneWidget);
    await tapVisible(tester, find.byKey(const Key('logoutButton')));
    expect(find.byKey(const Key('emailField')), findsOneWidget);
    expect(find.text('Amani'), findsNothing);
  });
}
