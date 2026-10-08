import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;

import 'helpers.dart';

// Fail loudly if a test ever taps something that isn't on screen.
void _strictTaps() => WidgetController.hitTestWarningShouldBeFatal = true;

Future<void> fillAndSubmit(
  WidgetTester tester, {
  required String email,
  required String password,
  String? confirm,
  bool register = false,
}) async {
  if (register) {
    await tester.tap(find.byKey(const Key('toggle_Register')));
    await tester.pumpAndSettle();
  }
  await tester.enterText(find.byKey(const Key('emailField')).last, email);
  await tester.enterText(find.byKey(const Key('passwordField')).last, password);
  if (register) {
    await tester.enterText(
      find.byKey(const Key('confirmField')).last,
      confirm ?? password,
    );
  }
  await tester.ensureVisible(find.byKey(const Key('submitButton')));
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(const Key('submitButton')));
  await tester.pumpAndSettle();
}

final success = {'token': 'tok-123', 'user': caregiverJson};

void main() {
  setUpAll(_strictTaps);

  testWidgets('shows log in when there is no saved session', (tester) async {
    await pumpApp(tester, FakeBackend((_) async => json({})));
    expect(find.text('Nurtura'), findsOneWidget);
    expect(find.byKey(const Key('emailField')), findsOneWidget);
    expect(find.byKey(const Key('confirmField')), findsNothing);
  });

  testWidgets('logs in, stores the token and shows the signed-in screen', (
    tester,
  ) async {
    final backend = FakeBackend((_) async => json(success));
    final store = await pumpApp(tester, backend);

    await fillAndSubmit(
      tester,
      email: '  Wanjiru@Example.com ',
      password: 'Str0ng-Passw0rd!',
    );

    final body = jsonDecode(backend.to('/api/auth/login/').single.body);
    expect(body, {
      'username': 'wanjiru@example.com',
      'password': 'Str0ng-Passw0rd!',
    });
    expect(store.token, 'tok-123');
    expect(find.text('Your children'), findsOneWidget);
  });

  testWidgets('wrong credentials show a clear message', (tester) async {
    await pumpApp(
      tester,
      FakeBackend(
        (_) async => json({
          'non_field_errors': ['Unable to log in with provided credentials.'],
        }, 400),
      ),
    );
    await fillAndSubmit(tester, email: 'a@b.co', password: 'nope');
    expect(
      find.text("That email and password don't match an account."),
      findsOneWidget,
    );
  });

  testWidgets('rate limiting shows how long to wait', (tester) async {
    await pumpApp(
      tester,
      FakeBackend(
        (_) async => json({
          'detail': 'Request was throttled. Expected available in 42 seconds.',
        }, 429),
      ),
    );
    await fillAndSubmit(tester, email: 'a@b.co', password: 'nope');
    expect(
      find.text('Too many attempts. Please wait 42 seconds and try again.'),
      findsOneWidget,
    );
  });

  testWidgets('email already in use is shown once, under the email field', (
    tester,
  ) async {
    await pumpApp(
      tester,
      FakeBackend(
        (_) async => json({
          'username': ['A user with that username already exists.'],
          'email': ['An account with this email already exists.'],
        }, 400),
      ),
    );
    await fillAndSubmit(
      tester,
      email: 'wanjiru@example.com',
      password: 'Str0ng-Passw0rd!',
      register: true,
    );
    expect(
      find.text('An account with this email already exists.'),
      findsOneWidget,
    );
    expect(
      find.text('A user with that username already exists.'),
      findsNothing,
    );
    expect(find.byKey(const Key('authError')), findsNothing);
  });

  testWidgets('weak password errors from the server appear under the field', (
    tester,
  ) async {
    await pumpApp(
      tester,
      FakeBackend(
        (_) async => json({
          'password': [
            'This password is too short. It must contain at least 8 characters.',
            'This password is too common.',
          ],
        }, 400),
      ),
    );
    await fillAndSubmit(
      tester,
      email: 'wanjiru@example.com',
      password: 'abc',
      register: true,
    );
    expect(
      find.text(
        'This password is too short. It must contain at least 8 characters. '
        'This password is too common.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('mismatched confirmation is caught before any request', (
    tester,
  ) async {
    final backend = FakeBackend((_) async => json(success));
    await pumpApp(tester, backend);
    await fillAndSubmit(
      tester,
      email: 'wanjiru@example.com',
      password: 'Str0ng-Passw0rd!',
      confirm: 'different',
      register: true,
    );
    expect(find.text("Passwords don't match."), findsOneWidget);
    expect(backend.requests, isEmpty);
  });

  testWidgets('registration sends the email as username and signs in', (
    tester,
  ) async {
    final backend = FakeBackend((_) async => json(success, 201));
    final store = await pumpApp(tester, backend);
    await fillAndSubmit(
      tester,
      email: 'Wanjiru@example.com',
      password: 'Str0ng-Passw0rd!',
      register: true,
    );
    final body = jsonDecode(backend.to('/api/auth/register/').single.body);
    expect(body['username'], 'wanjiru@example.com');
    expect(body['email'], 'wanjiru@example.com');
    expect(store.token, 'tok-123');
  });

  testWidgets('shows a spinner and ignores repeat taps while submitting', (
    tester,
  ) async {
    final pending = Completer<http.Response>();
    final backend = FakeBackend((_) => pending.future);
    await pumpApp(tester, backend);

    await tester.enterText(find.byKey(const Key('emailField')).last, 'a@b.co');
    await tester.enterText(find.byKey(const Key('passwordField')).last, 'pw');
    await tester.tap(find.byKey(const Key('submitButton')));
    await tester.pump();
    expect(find.byKey(const Key('buttonSpinner')), findsOneWidget);

    await tester.tap(find.byKey(const Key('submitButton')));
    await tester.pump();
    expect(backend.requests, hasLength(1));

    pending.complete(json(success));
    await tester.pumpAndSettle();
    expect(find.text('Your children'), findsOneWidget);
  });

  testWidgets('an unreachable server is reported, not a silent failure', (
    tester,
  ) async {
    await pumpApp(
      tester,
      FakeBackend(
        (_) async => throw http.ClientException('Connection refused'),
      ),
    );
    await fillAndSubmit(tester, email: 'a@b.co', password: 'pw');
    expect(
      find.text(
        "Can't reach the Nurtura server. Check your connection and try again.",
      ),
      findsOneWidget,
    );
  });

  testWidgets('restores a saved session, then logs out', (tester) async {
    final backend = FakeBackend(
      (request) async => switch (request.url.path) {
        '/api/auth/me/' => json(caregiverJson),
        _ => http.Response('', 204),
      },
    );
    final store = await pumpApp(tester, backend, savedToken: 'saved');

    expect(find.text('Your children'), findsOneWidget);
    expect(
      backend.to('/api/auth/me/').single.headers['Authorization'],
      'Token saved',
    );

    await tester.tap(find.byKey(const Key('logoutButton')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('emailField')), findsOneWidget);
    expect(store.token, isNull);
  });

  testWidgets('an expired saved token falls back to log in', (tester) async {
    final store = await pumpApp(
      tester,
      FakeBackend((_) async => json({'detail': 'Invalid token.'}, 401)),
      savedToken: 'expired',
    );
    expect(find.byKey(const Key('emailField')), findsOneWidget);
    expect(store.token, isNull);
  });
}
