import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/services/biometrics.dart';
import 'package:nurtura_app/state/fingerprint_store.dart';

import 'auth_screen_test.dart' show success;
import 'edit_and_delete_test.dart'
    show backendWith, childJson, openFamily, tapVisible;
import 'helpers.dart';

// Fingerprint log-in and lock (#150).

/// Stands in for the phone's fingerprint prompt.
class FakeBiometrics implements Biometrics {
  FakeBiometrics({this.isAvailable = true, this.pass = true, this.error});

  bool isAvailable;
  bool pass;
  String? error;
  final reasons = <String>[];

  @override
  Future<bool> available() async => isAvailable;

  @override
  Future<bool> check(String reason) async {
    reasons.add(reason);
    if (error != null) throw BiometricsError(error!);
    return pass;
  }
}

const wanjiru = 'wanjiru@example.com';

SavedFingerprint savedKey([String key = 'key-1']) =>
    SavedFingerprint(email: wanjiru, key: key);

/// The caregiver backend, plus the fingerprint routes: "key-1" logs in.
FakeBackend fingerprintBackend() => backendWith((r) async {
  switch ((r.method, r.url.path)) {
    case ('POST', '/api/auth/fingerprint/'):
      return json({'key': 'key-1'}, 201);
    case ('DELETE', '/api/auth/fingerprint/'):
      return http.Response('', 204);
    case ('POST', '/api/auth/fingerprint/login/'):
      final body = jsonDecode(r.body) as Map;
      return body['key'] == 'key-1'
          ? json(success)
          : json({
              'key': [
                'Fingerprint log-in is off on this phone. Log in with your '
                    'password.',
              ],
            }, 400);
    case ('POST', '/api/auth/logout/'):
      return http.Response('', 204);
  }
  return null;
}, children: [childJson()]);

Future<void> logOut(WidgetTester tester) async {
  await openFamily(tester);
  await tester.scrollUntilVisible(
    find.byKey(const Key('logoutButton')),
    200,
    scrollable: find.byType(Scrollable).last,
  );
  await tapVisible(tester, find.byKey(const Key('logoutButton')));
}

void main() {
  test('the saved email is shown partly hidden', () {
    expect(savedKey().maskedEmail, 'w***@example.com');
    expect(
      const SavedFingerprint(
        email: 'alysa.macharia@strathmore.edu',
        key: 'k',
      ).maskedEmail,
      'a***@strathmore.edu',
    );
    expect(
      const SavedFingerprint(email: 'broken', key: 'k').maskedEmail,
      'your account',
    );
  });

  setUpAll(() => WidgetController.hitTestWarningShouldBeFatal = true);

  group('the switch', () {
    testWidgets('is hidden when the phone has no fingerprint set up', (
      tester,
    ) async {
      await pumpApp(
        tester,
        fingerprintBackend(),
        savedToken: 'tok',
        biometrics: FakeBiometrics(isAvailable: false),
      );
      await openFamily(tester);
      expect(find.byKey(const Key('fingerprintLockSwitch')), findsNothing);
    });

    testWidgets('turns on after a scan and keeps the key securely', (
      tester,
    ) async {
      final store = MemoryFingerprintStore();
      final bio = FakeBiometrics();
      final backend = fingerprintBackend();
      await pumpApp(
        tester,
        backend,
        savedToken: 'tok',
        biometrics: bio,
        fingerprints: store,
      );
      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('fingerprintLockSwitch')));

      expect(bio.reasons, ['Confirm your fingerprint for Nurtura']);
      expect(jsonDecode(backend.to('/api/auth/fingerprint/').single.body), {
        'device_id': testDeviceId,
      });
      expect(store.saved?.email, wanjiru);
      expect(store.saved?.key, 'key-1');
      expect(
        find.text('Fingerprint log-in is on for this phone.'),
        findsOneWidget,
      );
      expect(find.byKey(const Key('lockScreen')), findsNothing);
    });

    testWidgets('stays off if the scan fails, and asks the server nothing', (
      tester,
    ) async {
      final store = MemoryFingerprintStore();
      final backend = fingerprintBackend();
      await pumpApp(
        tester,
        backend,
        savedToken: 'tok',
        biometrics: FakeBiometrics(pass: false),
        fingerprints: store,
      );
      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('fingerprintLockSwitch')));

      expect(store.saved, isNull);
      expect(backend.to('/api/auth/fingerprint/'), isEmpty);
      expect(find.text("Fingerprint log-in wasn't turned on."), findsOneWidget);
    });

    testWidgets('turning it off revokes the key', (tester) async {
      final store = MemoryFingerprintStore(savedKey());
      final backend = fingerprintBackend();
      await pumpApp(
        tester,
        backend,
        savedToken: 'tok',
        biometrics: FakeBiometrics(),
        fingerprints: store,
      );
      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('fingerprintLockSwitch')));

      expect(store.saved, isNull);
      expect(
        backend.to('/api/auth/fingerprint/').map((r) => r.method),
        contains('DELETE'),
      );
    });
  });

  group('log in with fingerprint', () {
    testWidgets('logging out keeps it, and the login screen offers it', (
      tester,
    ) async {
      final store = MemoryFingerprintStore(savedKey());
      final bio = FakeBiometrics();
      final backend = fingerprintBackend();
      final tokens = await pumpApp(
        tester,
        backend,
        savedToken: 'tok',
        biometrics: bio,
        fingerprints: store,
      );
      // Opening the app unlocks with the fingerprint.
      expect(bio.reasons, ['Unlock Nurtura']);

      await logOut(tester);
      expect(store.saved, isNotNull);
      // Logging out on purpose doesn't pop the prompt up again.
      expect(bio.reasons, ['Unlock Nurtura']);
      expect(find.text('Log in with fingerprint'), findsOneWidget);
      // Partly hidden: anyone holding the phone can see this screen.
      expect(find.text('w***@example.com'), findsOneWidget);
      expect(find.text(wanjiru), findsNothing);

      await tapVisible(tester, find.byKey(const Key('fingerprintLoginButton')));
      expect(bio.reasons.last, 'Log in to Nurtura');
      expect(
        jsonDecode(backend.to('/api/auth/fingerprint/login/').single.body),
        {'device_id': testDeviceId, 'key': 'key-1'},
      );
      expect(tokens.token, 'tok-123');
      expect(find.byKey(const Key('tab_family')), findsOneWidget);
    });

    testWidgets('opening the app logged out asks for the fingerprint', (
      tester,
    ) async {
      final bio = FakeBiometrics();
      final tokens = await pumpApp(
        tester,
        fingerprintBackend(),
        biometrics: bio,
        fingerprints: MemoryFingerprintStore(savedKey()),
      );
      expect(bio.reasons, ['Log in to Nurtura']);
      expect(tokens.token, 'tok-123');
    });

    testWidgets('a closed prompt leaves the password form', (tester) async {
      final tokens = await pumpApp(
        tester,
        fingerprintBackend(),
        biometrics: FakeBiometrics(pass: false),
        fingerprints: MemoryFingerprintStore(savedKey()),
      );
      expect(tokens.token, isNull);
      expect(find.byKey(const Key('emailField')), findsOneWidget);
      expect(find.text('Log in with fingerprint'), findsOneWidget);
    });

    testWidgets('a revoked key says so and stops offering it', (tester) async {
      final store = MemoryFingerprintStore(savedKey('key-old'));
      final tokens = await pumpApp(
        tester,
        fingerprintBackend(),
        biometrics: FakeBiometrics(),
        fingerprints: store,
      );
      expect(tokens.token, isNull);
      expect(store.saved, isNull);
      expect(find.textContaining('Fingerprint log-in is off'), findsOneWidget);
      expect(find.byKey(const Key('fingerprintLoginButton')), findsNothing);
    });

    testWidgets('is not offered when registering', (tester) async {
      await pumpApp(
        tester,
        fingerprintBackend(),
        biometrics: FakeBiometrics(pass: false),
        fingerprints: MemoryFingerprintStore(savedKey()),
      );
      await tapVisible(tester, find.byKey(const Key('toggle_Register')));
      expect(find.byKey(const Key('fingerprintLoginButton')), findsNothing);
    });
  });

  group('the lock screen', () {
    testWidgets('stays locked when the prompt is closed, and can retry', (
      tester,
    ) async {
      final bio = FakeBiometrics(pass: false);
      await pumpApp(
        tester,
        fingerprintBackend(),
        savedToken: 'tok',
        biometrics: bio,
        fingerprints: MemoryFingerprintStore(savedKey()),
      );
      expect(find.text('Nurtura is locked'), findsOneWidget);
      expect(find.byKey(const Key('tab_family')), findsNothing);

      bio.pass = true;
      await tapVisible(tester, find.byKey(const Key('unlockButton')));
      expect(find.byKey(const Key('lockScreen')), findsNothing);
    });

    testWidgets('explains a lockout', (tester) async {
      await pumpApp(
        tester,
        fingerprintBackend(),
        savedToken: 'tok',
        biometrics: FakeBiometrics(error: 'Too many tries.'),
        fingerprints: MemoryFingerprintStore(savedKey()),
      );
      expect(find.text('Too many tries.'), findsOneWidget);
    });

    testWidgets(
      '"Use password instead" logs out but keeps fingerprint log-in',
      (tester) async {
        final store = MemoryFingerprintStore(savedKey());
        final tokens = await pumpApp(
          tester,
          fingerprintBackend(),
          savedToken: 'tok',
          biometrics: FakeBiometrics(pass: false),
          fingerprints: store,
        );
        await tapVisible(tester, find.byKey(const Key('usePasswordInstead')));
        expect(tokens.token, isNull);
        expect(find.byKey(const Key('emailField')), findsOneWidget);
        expect(store.saved, isNotNull);
      },
    );
  });

  testWidgets('deleting the account forgets the key', (tester) async {
    final store = MemoryFingerprintStore(savedKey());
    await pumpApp(
      tester,
      backendWith((r) async {
        if (r.method == 'DELETE' && r.url.path == '/api/auth/me/') {
          return http.Response('', 204);
        }
        return null;
      }, children: [childJson()]),
      savedToken: 'tok',
      biometrics: FakeBiometrics(),
      fingerprints: store,
    );
    await openFamily(tester);
    await tester.scrollUntilVisible(
      find.byKey(const Key('deleteAccountButton')),
      200,
      scrollable: find.byType(Scrollable).last,
    );
    await tapVisible(tester, find.byKey(const Key('deleteAccountButton')));
    await tester.enterText(
      find.byKey(const Key('deleteAccountField')).last,
      'x-test-pass',
    );
    await tapVisible(tester, find.byKey(const Key('confirmDeleteAccount')));
    expect(store.saved, isNull);
  });
}
