import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'auth_screen_test.dart' show success;
import 'children_screen_test.dart' show tapVisible;
import 'helpers.dart';

Map<String, dynamic> resetChallenge({int resendAfter = 30}) => {
  'challenge': 'reset-abc',
  'email_hint': 'w***@example.com',
  'expires_in': 600,
  'resend_after': resendAfter,
};

/// A backend that sends reset codes and accepts [goodCode].
FakeBackend resetBackend({String goodCode = '123456', int resendAfter = 30}) =>
    FakeBackend((r) async {
      switch (r.url.path) {
        case '/api/auth/password-reset/':
          return json(resetChallenge(resendAfter: resendAfter), 202);
        case '/api/auth/password-reset/resend/':
          return json(resetChallenge(resendAfter: resendAfter));
        case '/api/auth/password-reset/confirm/':
          final body = jsonDecode(r.body) as Map;
          if (body['new_password'] == 'password') {
            return json({
              'new_password': ['This password is too common.'],
            }, 400);
          }
          return body['code'] == goodCode
              ? json({...success, 'device_trusted_until': null})
              : json({
                  'code': ["That code isn't right. You have 4 tries left."],
                }, 400);
      }
      return http.Response('', 404);
    });

Future<void> openReset(WidgetTester tester, {String email = ''}) async {
  if (email.isNotEmpty) {
    await tester.enterText(find.byKey(const Key('emailField')), email);
  }
  await tapVisible(tester, find.byKey(const Key('forgotPasswordButton')));
}

Future<void> askForCode(WidgetTester tester) async {
  await openReset(tester, email: 'Wanjiru@Example.com');
  await tapVisible(tester, find.byKey(const Key('sendResetCodeButton')));
}

Future<void> fillReset(
  WidgetTester tester, {
  String code = '123456',
  String password = 'Fresh-Passw0rd-2026',
  String? confirm,
}) async {
  await tester.enterText(find.byKey(const Key('codeField')), code);
  await tester.enterText(find.byKey(const Key('newPasswordField')), password);
  await tester.enterText(
    find.byKey(const Key('confirmNewPasswordField')),
    confirm ?? password,
  );
  await tapVisible(tester, find.byKey(const Key('resetPasswordButton')));
}

void main() {
  testWidgets('a forgotten password is reset with the emailed code', (
    tester,
  ) async {
    final backend = resetBackend();
    final store = await pumpApp(tester, backend);
    await askForCode(tester);

    expect(jsonDecode(backend.to('/api/auth/password-reset/').single.body), {
      'email': 'wanjiru@example.com',
    });
    expect(find.text('Check your email'), findsOneWidget);
    expect(find.textContaining('w***@example.com'), findsOneWidget);

    await fillReset(tester);
    expect(
      jsonDecode(backend.to('/api/auth/password-reset/confirm/').single.body),
      {
        'challenge': 'reset-abc',
        'code': '123456',
        'new_password': 'Fresh-Passw0rd-2026',
        'device_id': testDeviceId,
        'remember_device': true,
      },
    );
    expect(store.token, 'tok-123');
    expect(find.text('Your children'), findsOneWidget);
    expect(find.byKey(const Key('resetPasswordButton')), findsNothing);
  });

  testWidgets('the email typed on the login form is carried over', (
    tester,
  ) async {
    await pumpApp(tester, resetBackend());
    await openReset(tester, email: 'wanjiru@example.com');
    final field = tester.widget<TextField>(
      find.descendant(
        of: find.byKey(const Key('resetEmailField')),
        matching: find.byType(TextField),
      ),
    );
    expect(field.controller!.text, 'wanjiru@example.com');
  });

  testWidgets('the email is checked before anything is sent', (tester) async {
    final backend = resetBackend();
    await pumpApp(tester, backend);
    await openReset(tester);
    await tapVisible(tester, find.byKey(const Key('sendResetCodeButton')));
    expect(find.text('Enter your email address.'), findsOneWidget);
    expect(backend.to('/api/auth/password-reset/'), isEmpty);
  });

  testWidgets('a wrong code is explained and the code cleared', (tester) async {
    final backend = resetBackend();
    final store = await pumpApp(tester, backend);
    await askForCode(tester);
    await fillReset(tester, code: '000000');
    expect(find.textContaining('4 tries left'), findsOneWidget);
    expect(store.token, isNull);
  });

  testWidgets('a password the server refuses shows under the field', (
    tester,
  ) async {
    await pumpApp(tester, resetBackend());
    await askForCode(tester);
    await fillReset(tester, password: 'password');
    expect(find.text('This password is too common.'), findsOneWidget);
    expect(find.byKey(const Key('resetError')), findsNothing);
  });

  testWidgets('the two new passwords must match', (tester) async {
    final backend = resetBackend();
    await pumpApp(tester, backend);
    await askForCode(tester);
    await fillReset(tester, confirm: 'something-else');
    expect(find.text("Passwords don't match."), findsOneWidget);
    expect(backend.to('/api/auth/password-reset/confirm/'), isEmpty);
  });

  testWidgets('a new code can be sent after the wait', (tester) async {
    final backend = resetBackend(resendAfter: 0);
    await pumpApp(tester, backend);
    await askForCode(tester);
    await tapVisible(tester, find.byKey(const Key('resetResendButton')));
    expect(
      jsonDecode(backend.to('/api/auth/password-reset/resend/').single.body),
      {'challenge': 'reset-abc'},
    );
    expect(find.text('A new code is on its way.'), findsOneWidget);
  });

  testWidgets('back returns to the login form', (tester) async {
    await pumpApp(tester, resetBackend());
    await openReset(tester);
    await tapVisible(tester, find.byKey(const Key('resetBack')));
    expect(find.byKey(const Key('submitButton')), findsOneWidget);
  });

  // Password managers (e.g. Google's "Suggest strong password") need the
  // account and both new-password fields in one autofill group (#128).
  Iterable<String>? hintsOf(WidgetTester tester, String key) => tester
      .widget<TextField>(
        find.descendant(
          of: find.byKey(Key(key)),
          matching: find.byType(TextField),
        ),
      )
      .autofillHints;

  testWidgets(
    'the reset step offers the account and new passwords to autofill',
    (tester) async {
      await pumpApp(tester, resetBackend());
      await askForCode(tester);
      final account = tester.widget<TextField>(
        find.descendant(
          of: find.byKey(const Key('resetAccountField')),
          matching: find.byType(TextField),
        ),
      );
      expect(account.readOnly, isTrue);
      expect(account.controller!.text, 'Wanjiru@Example.com');
      expect(account.autofillHints, contains(AutofillHints.username));
      for (final key in ['newPasswordField', 'confirmNewPasswordField']) {
        expect(hintsOf(tester, key), [AutofillHints.newPassword]);
      }
      for (final key in [
        'resetAccountField',
        'newPasswordField',
        'confirmNewPasswordField',
      ]) {
        expect(
          find.ancestor(
            of: find.byKey(Key(key)),
            matching: find.byType(AutofillGroup),
          ),
          findsOneWidget,
        );
      }
    },
  );

  testWidgets(
    'registering offers the email and both new passwords to autofill',
    (tester) async {
      await pumpApp(tester, resetBackend());
      await tapVisible(tester, find.text('Register'));
      expect(hintsOf(tester, 'emailField'), contains(AutofillHints.username));
      expect(hintsOf(tester, 'passwordField'), [AutofillHints.newPassword]);
      expect(hintsOf(tester, 'confirmField'), [AutofillHints.newPassword]);
    },
  );
}
