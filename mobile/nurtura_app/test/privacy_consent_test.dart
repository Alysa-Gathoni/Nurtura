import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/utils/dates.dart' as dates;

import 'helpers.dart';

// The privacy notice and agreeing to it before using the app (#136).

Map<String, dynamic> noticeJson({String version = '2026-10-26'}) => {
  'version': version,
  'title': 'How Nurtura uses your information',
  'sections': [
    {'heading': 'What we keep', 'body': 'Your email and your children.'},
    {'heading': 'How long we keep it', 'body': 'Until you delete it.'},
  ],
};

const caregiverToAsk = {...caregiverJson, 'privacy_consent_required': true};

Future<void> tapVisible(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.pumpAndSettle();
  await tester.tap(finder);
  await tester.pumpAndSettle();
}

FakeBackend backendWith(
  Future<http.Response?> Function(http.Request r) extra, {
  Map<String, dynamic> me = caregiverToAsk,
  List<Map<String, dynamic>> children = const [],
}) => FakeBackend((r) async {
  final answer = await extra(r);
  if (answer != null) return answer;
  if (r.url.path == '/api/auth/me/') return json(me);
  if (r.url.path == '/api/privacy-notice/') return json(noticeJson());
  if (r.url.path == '/api/auth/privacy-consent/') {
    return json({...caregiverJson, 'privacy_consent_required': false});
  }
  if (r.url.path == '/api/auth/logout/') return http.Response('', 204);
  return json({'detail': 'Not found.'}, 404);
}, children: children);

Finder get agreeButton => find.byKey(const Key('privacyAgreeButton'));

void main() {
  setUpAll(() => WidgetController.hitTestWarningShouldBeFatal = true);
  setUp(() => dates.clock = () => DateTime(2026, 10, 1, 9));
  tearDown(() => dates.clock = DateTime.now);

  testWidgets('a caregiver who has not agreed sees the notice first', (
    tester,
  ) async {
    final backend = backendWith((_) async => null);
    await pumpApp(tester, backend, savedToken: 'tok');

    expect(find.text('Before you start'), findsOneWidget);
    expect(find.text('How long we keep it'), findsOneWidget);
    expect(find.text('Until you delete it.'), findsOneWidget);
    expect(find.byKey(const Key('tab_today')), findsNothing);
    // Nothing about the children is fetched before agreeing.
    expect(backend.to('/api/children/'), isEmpty);
  });

  testWidgets('agreeing needs the box ticked, then opens the app', (
    tester,
  ) async {
    final backend = backendWith((_) async => null);
    await pumpApp(tester, backend, savedToken: 'tok');

    await tapVisible(tester, agreeButton);
    expect(backend.to('/api/auth/privacy-consent/'), isEmpty);

    await tapVisible(tester, find.byKey(const Key('privacyAgreeCheckbox')));
    await tapVisible(tester, agreeButton);

    final post = backend.to('/api/auth/privacy-consent/').single;
    expect(jsonDecode(post.body), {'version': '2026-10-26'});
    expect(find.text('Before you start'), findsNothing);
    expect(find.text('Add your first child'), findsOneWidget);
  });

  testWidgets('"Not now" logs out', (tester) async {
    final backend = backendWith((_) async => null);
    final store = await pumpApp(tester, backend, savedToken: 'tok');

    await tapVisible(tester, find.byKey(const Key('privacyLogout')));

    expect(backend.to('/api/auth/logout/'), hasLength(1));
    expect(store.token, isNull);
    expect(find.byKey(const Key('submitButton')), findsOneWidget);
  });

  testWidgets('if the notice changed meanwhile, the new one is shown', (
    tester,
  ) async {
    var notices = 0;
    final backend = backendWith((r) async {
      if (r.url.path == '/api/privacy-notice/') {
        notices++;
        return json(
          noticeJson(version: notices == 1 ? '2026-10-26' : '2026-12-01'),
        );
      }
      if (r.url.path == '/api/auth/privacy-consent/') {
        return json({
          'version': [
            'The privacy notice has changed. Please read the new version.',
          ],
        }, 400);
      }
      return null;
    });
    await pumpApp(tester, backend, savedToken: 'tok');
    await tapVisible(tester, find.byKey(const Key('privacyAgreeCheckbox')));
    await tapVisible(tester, agreeButton);

    expect(
      find.text('The privacy notice has changed. Please read the new version.'),
      findsOneWidget,
    );
    expect(notices, 2);
    // The box must be ticked again for the new wording.
    await tapVisible(tester, agreeButton);
    expect(backend.to('/api/auth/privacy-consent/'), hasLength(1));
    await tapVisible(tester, find.byKey(const Key('privacyAgreeCheckbox')));
    await tapVisible(tester, agreeButton);
    expect(jsonDecode(backend.to('/api/auth/privacy-consent/').last.body), {
      'version': '2026-12-01',
    });
  });

  testWidgets('a notice that fails to load can be retried', (tester) async {
    var notices = 0;
    final backend = backendWith((r) async {
      if (r.url.path == '/api/privacy-notice/' && notices++ == 0) {
        return json({'detail': 'Server error.'}, 500);
      }
      return null;
    });
    await pumpApp(tester, backend, savedToken: 'tok');

    expect(find.byKey(const Key('privacyLoadError')), findsOneWidget);
    await tapVisible(tester, find.byKey(const Key('privacyRetry')));
    expect(find.text('What we keep'), findsOneWidget);
  });

  testWidgets('the Family tab opens the notice to read', (tester) async {
    final backend = backendWith(
      (_) async => null,
      me: {...caregiverJson, 'privacy_consent_required': false},
      children: [
        {
          'id': 3,
          'name': 'Amani',
          'date_of_birth': '2025-08-01',
          'interests': [],
          'concerns': [],
        },
      ],
    );
    await pumpApp(tester, backend, savedToken: 'tok');
    await tapVisible(tester, find.byKey(const Key('tab_family')));
    final link = find.byKey(const Key('privacyNoticeButton'));
    await tester.scrollUntilVisible(
      link,
      200,
      scrollable: find.byType(Scrollable).last,
    );
    await tapVisible(tester, link);

    expect(find.text('Privacy notice'), findsOneWidget);
    expect(find.text('Until you delete it.'), findsOneWidget);
    expect(find.byKey(const Key('privacyAgreeCheckbox')), findsNothing);
  });
}
