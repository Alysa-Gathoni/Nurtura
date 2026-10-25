import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/services/api_client.dart';
import 'package:nurtura_app/services/google_auth.dart';

import 'auth_screen_test.dart' show success;
import 'children_screen_test.dart' show tapVisible;
import 'helpers.dart';

/// Stands in for Google: returns [token], or null as if the chooser was
/// closed, or throws [error].
class FakeGoogle implements GoogleIdTokens {
  FakeGoogle({this.token = 'google-id-token', this.error});

  final String? token;
  final ApiException? error;
  int signOuts = 0;

  @override
  Future<String?> idToken() async {
    if (error != null) throw error!;
    return token;
  }

  @override
  Future<void> signOut() async => signOuts++;
}

FakeBackend googleBackend({int status = 200, Map<String, dynamic>? body}) =>
    FakeBackend((r) async {
      if (r.url.path == '/api/auth/google/') {
        return json(
          body ?? {...success, 'device_trusted_until': null, 'created': false},
          status,
        );
      }
      if (r.url.path == '/api/auth/logout/') return http.Response('', 204);
      return http.Response('', 404);
    });

void main() {
  testWidgets('without a client ID there is no Google button', (tester) async {
    await pumpApp(tester, googleBackend());
    expect(find.byKey(const Key('googleButton')), findsNothing);
    // The email form is unchanged.
    expect(find.byKey(const Key('submitButton')), findsOneWidget);
  });

  testWidgets('Google is offered next to email on both tabs', (tester) async {
    await pumpApp(tester, googleBackend(), google: FakeGoogle());
    expect(find.byKey(const Key('googleButton')), findsOneWidget);
    expect(find.text('or'), findsOneWidget);
    expect(find.byKey(const Key('emailField')), findsOneWidget);
    await tapVisible(tester, find.text('Register'));
    expect(find.byKey(const Key('googleButton')), findsOneWidget);
    expect(find.byKey(const Key('confirmField')), findsOneWidget);
  });

  testWidgets('Continue with Google signs in without an emailed code', (
    tester,
  ) async {
    final backend = googleBackend();
    final store = await pumpApp(tester, backend, google: FakeGoogle());
    await tapVisible(tester, find.byKey(const Key('googleButton')));
    expect(jsonDecode(backend.to('/api/auth/google/').single.body), {
      'id_token': 'google-id-token',
      'device_id': testDeviceId,
      'remember_device': true,
    });
    expect(store.token, 'tok-123');
    expect(find.text('Your children'), findsOneWidget);
    expect(find.byKey(const Key('codeField')), findsNothing);
  });

  testWidgets('closing Google\'s chooser leaves the login form as it was', (
    tester,
  ) async {
    final backend = googleBackend();
    await pumpApp(tester, backend, google: FakeGoogle(token: null));
    await tapVisible(tester, find.byKey(const Key('googleButton')));
    expect(backend.to('/api/auth/google/'), isEmpty);
    expect(find.byKey(const Key('authError')), findsNothing);
    expect(find.byKey(const Key('submitButton')), findsOneWidget);
  });

  testWidgets('a refusal (e.g. an administrator) is shown, and the Google '
      'account forgotten', (tester) async {
    final google = FakeGoogle();
    final store = await pumpApp(
      tester,
      googleBackend(
        status: 400,
        body: {
          'non_field_errors': [
            'Administrators sign in with email and password, then the '
                'emailed code.',
          ],
        },
      ),
      google: google,
    );
    await tapVisible(tester, find.byKey(const Key('googleButton')));
    expect(find.textContaining('Administrators sign in'), findsOneWidget);
    expect(store.token, isNull);
    expect(google.signOuts, 1);
  });

  testWidgets('a problem on Google\'s side is shown', (tester) async {
    await pumpApp(
      tester,
      googleBackend(),
      google: FakeGoogle(
        error: ApiException(
          "Google sign-in didn't work. Please try again, or use your email.",
        ),
      ),
    );
    await tapVisible(tester, find.byKey(const Key('googleButton')));
    expect(find.textContaining("Google sign-in didn't work"), findsOneWidget);
  });

  testWidgets('logging out also forgets the Google account', (tester) async {
    final google = FakeGoogle();
    await pumpApp(tester, googleBackend(), google: google);
    await tapVisible(tester, find.byKey(const Key('googleButton')));
    expect(find.text('Your children'), findsOneWidget);
    await tapVisible(tester, find.byKey(const Key('logoutButton')));
    expect(find.byKey(const Key('googleButton')), findsOneWidget);
    expect(google.signOuts, 1);
  });
}
