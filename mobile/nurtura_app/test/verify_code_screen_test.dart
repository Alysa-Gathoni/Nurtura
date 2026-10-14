import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/state/preferences.dart';

import 'auth_screen_test.dart' show fillAndSubmit, success;
import 'helpers.dart';

Map<String, dynamic> challengeJson({int resendAfter = 30}) => {
  'two_factor_required': true,
  'challenge': 'chal-abc',
  'email_hint': 'w***@example.com',
  'expires_in': 600,
  'resend_after': resendAfter,
};

/// A backend that asks for a code at login and accepts [goodCode].
FakeBackend codeBackend({String goodCode = '123456', int resendAfter = 30}) =>
    FakeBackend((r) async {
      switch (r.url.path) {
        case '/api/auth/login/':
          return json(challengeJson(resendAfter: resendAfter), 202);
        case '/api/auth/register/':
          return json(challengeJson(resendAfter: resendAfter), 201);
        case '/api/auth/login/verify/':
          final code = jsonDecode(r.body)['code'];
          return code == goodCode
              ? json({...success, 'device_trusted_until': null})
              : json({
                  'code': ['That code is not right. 4 tries left.'],
                }, 400);
        case '/api/auth/login/resend/':
          return json(challengeJson(resendAfter: resendAfter));
      }
      return http.Response('', 404);
    });

Future<void> logIn(WidgetTester tester) => fillAndSubmit(
  tester,
  email: 'wanjiru@example.com',
  password: 'Str0ng-Passw0rd!',
);

Future<void> enterCode(WidgetTester tester, String code) async {
  await tester.enterText(find.byKey(const Key('codeField')), code);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('a new phone is asked for the emailed code, then signs in', (
    tester,
  ) async {
    final backend = codeBackend();
    final store = await pumpApp(tester, backend);
    await logIn(tester);

    expect(find.text('Check your email'), findsOneWidget);
    expect(find.textContaining('w***@example.com'), findsOneWidget);
    expect(store.token, isNull);

    // Six digits submit on their own.
    await enterCode(tester, '123456');
    expect(jsonDecode(backend.to('/api/auth/login/verify/').single.body), {
      'challenge': 'chal-abc',
      'code': '123456',
      'device_id': testDeviceId,
      'remember_device': true,
    });
    expect(store.token, 'tok-123');
    expect(find.text('Your children'), findsOneWidget);
  });

  testWidgets('registering also goes through the code step', (tester) async {
    final backend = codeBackend();
    await pumpApp(tester, backend);
    await fillAndSubmit(
      tester,
      email: 'wanjiru@example.com',
      password: 'Str0ng-Passw0rd!',
      register: true,
    );
    expect(
      jsonDecode(backend.to('/api/auth/register/').single.body)['device_id'],
      testDeviceId,
    );
    expect(find.byKey(const Key('codeField')), findsOneWidget);
  });

  testWidgets('a wrong code shows the server message and clears the boxes', (
    tester,
  ) async {
    final store = await pumpApp(tester, codeBackend());
    await logIn(tester);
    await enterCode(tester, '000000');

    expect(find.text('That code is not right. 4 tries left.'), findsOneWidget);
    expect(store.token, isNull);
    expect(find.text('0'), findsNothing); // the boxes are empty again

    await enterCode(tester, '123456');
    expect(store.token, 'tok-123');
  });

  testWidgets('letters are ignored and a short code is not sent', (
    tester,
  ) async {
    final backend = codeBackend();
    await pumpApp(tester, backend);
    await logIn(tester);
    await enterCode(tester, '12ab3');
    await tester.tap(find.byKey(const Key('verifyButton')));
    await tester.pumpAndSettle();
    expect(find.text('Enter all six digits from the email.'), findsOneWidget);
    expect(backend.to('/api/auth/login/verify/'), isEmpty);
  });

  testWidgets('the phone is only trusted when the caregiver chooses', (
    tester,
  ) async {
    final backend = codeBackend();
    await pumpApp(tester, backend);
    await logIn(tester);
    await tester.tap(find.byKey(const Key('rememberDevice')));
    await tester.pumpAndSettle();
    await enterCode(tester, '123456');
    expect(
      jsonDecode(
        backend.to('/api/auth/login/verify/').single.body,
      )['remember_device'],
      isFalse,
    );
  });

  testWidgets('a new code can be sent once the countdown ends', (tester) async {
    final backend = codeBackend(resendAfter: 3);
    await pumpApp(tester, backend);
    await logIn(tester);

    final resend = find.byKey(const Key('resendButton'));
    expect(tester.widget<TextButton>(resend).onPressed, isNull);
    expect(find.textContaining('Send a new code in'), findsOneWidget);

    await tester.pump(const Duration(seconds: 4));
    expect(tester.widget<TextButton>(resend).onPressed, isNotNull);
    await tester.ensureVisible(resend);
    await tester.pump();
    await tester.tap(resend);
    await tester.pump();
    await tester.pump();

    expect(jsonDecode(backend.to('/api/auth/login/resend/').single.body), {
      'challenge': 'chal-abc',
    });
    expect(find.text('A new code is on its way.'), findsOneWidget);
    // The countdown starts again.
    expect(tester.widget<TextButton>(resend).onPressed, isNull);
    await tester.pumpAndSettle();
  });

  testWidgets('"Use a different account" goes back to log in', (tester) async {
    await pumpApp(tester, codeBackend());
    await logIn(tester);
    await tester.ensureVisible(find.byKey(const Key('differentAccountButton')));
    await tester.pump();
    await tester.tap(find.byKey(const Key('differentAccountButton')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('emailField')), findsOneWidget);
    expect(find.byKey(const Key('codeField')), findsNothing);
  });

  testWidgets('the code screen works in dark mode', (tester) async {
    await pumpApp(
      tester,
      codeBackend(),
      preferences: MemoryPreferences({'nurtura.themeMode': 'dark'}),
    );
    await logIn(tester);
    final context = tester.element(find.text('Check your email'));
    expect(Theme.of(context).brightness, Brightness.dark);
    expect(tester.takeException(), isNull);
  });
}
