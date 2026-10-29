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

/// A backend that sends reset codes, swaps [goodCode] for [passToken]
/// (#146), and sets a password with the pass "pass-1".
FakeBackend resetBackend({
  String goodCode = '123456',
  int resendAfter = 30,
  String passToken = 'pass-1',
}) => FakeBackend((r) async {
  switch (r.url.path) {
    case '/api/auth/password-reset/':
      return json(resetChallenge(resendAfter: resendAfter), 202);
    case '/api/auth/password-reset/resend/':
      return json(resetChallenge(resendAfter: resendAfter));
    case '/api/auth/password-reset/verify/':
      final body = jsonDecode(r.body) as Map;
      return body['code'] == goodCode
          ? json({'reset_token': passToken, 'expires_in': 600})
          : json({
              'code': ["That code isn't right. You have 4 tries left."],
            }, 400);
    case '/api/auth/password-reset/confirm/':
      final body = jsonDecode(r.body) as Map;
      if (body['new_password'] == 'password') {
        return json({
          'new_password': ['This password is too common.'],
        }, 400);
      }
      return body['reset_token'] == 'pass-1'
          ? json({...success, 'device_trusted_until': null})
          : json({
              'reset_token': [
                'This reset has expired. Ask for a new code to try again.',
              ],
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

/// Step 2: typing the sixth digit checks the code (#146).
Future<void> enterCode(WidgetTester tester, [String code = '123456']) async {
  await tester.enterText(find.byKey(const Key('codeField')), code);
  await tester.pumpAndSettle();
}

/// Step 3: the new password, then save.
Future<void> fillPasswords(
  WidgetTester tester, {
  String password = 'Fresh-Passw0rd-2026',
  String? confirm,
}) async {
  await tester.enterText(find.byKey(const Key('newPasswordField')), password);
  await tester.enterText(
    find.byKey(const Key('confirmNewPasswordField')),
    confirm ?? password,
  );
  // Let the strength meter finish opening: it moves the button.
  await tester.pumpAndSettle();
  await tapVisible(tester, find.byKey(const Key('resetPasswordButton')));
}

/// Steps 2 and 3: the code, then the new password.
Future<void> fillReset(
  WidgetTester tester, {
  String code = '123456',
  String password = 'Fresh-Passw0rd-2026',
  String? confirm,
}) async {
  await enterCode(tester, code);
  await fillPasswords(tester, password: password, confirm: confirm);
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

    await enterCode(tester);
    expect(
      jsonDecode(backend.to('/api/auth/password-reset/verify/').single.body),
      {'challenge': 'reset-abc', 'code': '123456'},
    );
    expect(find.text('Choose a new password'), findsOneWidget);
    expect(find.byKey(const Key('codeField')), findsNothing);

    await fillPasswords(tester);
    expect(
      jsonDecode(backend.to('/api/auth/password-reset/confirm/').single.body),
      {
        'reset_token': 'pass-1',
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
    await enterCode(tester, '000000');
    expect(find.textContaining('4 tries left'), findsOneWidget);
    // Still on the code step, with the boxes empty for another try.
    expect(find.text('Check your email'), findsOneWidget);
    expect(find.byKey(const Key('newPasswordField')), findsNothing);
    expect(
      tester
          .widget<TextField>(find.byKey(const Key('codeField')))
          .controller!
          .text,
      isEmpty,
    );
    // The keyboard comes back for the next try.
    expect(
      tester
          .widget<TextField>(find.byKey(const Key('codeField')))
          .focusNode!
          .hasFocus,
      isTrue,
    );
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

  testWidgets('Continue with part of the code asks for all six digits', (
    tester,
  ) async {
    final backend = resetBackend();
    await pumpApp(tester, backend);
    await askForCode(tester);
    await enterCode(tester, '123');
    await tapVisible(tester, find.byKey(const Key('checkResetCodeButton')));
    expect(find.text('Enter all six digits from the email.'), findsOneWidget);
    expect(backend.to('/api/auth/password-reset/verify/'), isEmpty);
  });

  testWidgets('an expired pass goes back to ask for a new code', (
    tester,
  ) async {
    final backend = resetBackend(passToken: 'pass-old');
    final store = await pumpApp(tester, backend);
    await askForCode(tester);
    await fillReset(tester);
    expect(find.textContaining('This reset has expired'), findsOneWidget);
    expect(find.byKey(const Key('sendResetCodeButton')), findsOneWidget);
    expect(store.token, isNull);
  });

  testWidgets('the dots show which of the three steps this is', (tester) async {
    await pumpApp(tester, resetBackend());
    await openReset(tester, email: 'wanjiru@example.com');
    expect(find.bySemanticsLabel('Step 1 of 3'), findsOneWidget);
    await tapVisible(tester, find.byKey(const Key('sendResetCodeButton')));
    expect(find.bySemanticsLabel('Step 2 of 3'), findsOneWidget);
    await enterCode(tester);
    expect(find.bySemanticsLabel('Step 3 of 3'), findsOneWidget);
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
      await enterCode(tester);
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
