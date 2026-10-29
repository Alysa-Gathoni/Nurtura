import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/services/biometrics.dart';
import 'package:nurtura_app/state/app_lock.dart';
import 'package:nurtura_app/state/preferences.dart';

import 'edit_and_delete_test.dart'
    show backendWith, childJson, openFamily, tapVisible;
import 'helpers.dart';

// Unlock with fingerprint (#150).

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

FakeBackend familyBackend() => backendWith((r) async {
  if (r.url.path == '/api/auth/logout/') return http.Response('', 204);
  return null;
}, children: [childJson()]);

MemoryPreferences lockedOn() => MemoryPreferences({AppLock.prefKey: 'on'});

void main() {
  setUpAll(() => WidgetController.hitTestWarningShouldBeFatal = true);

  group('the switch', () {
    testWidgets('is hidden when the phone has no fingerprint set up', (
      tester,
    ) async {
      await pumpApp(
        tester,
        familyBackend(),
        savedToken: 'tok',
        biometrics: FakeBiometrics(isAvailable: false),
      );
      await openFamily(tester);
      expect(find.byKey(const Key('fingerprintLockSwitch')), findsNothing);
    });

    testWidgets('turns on after a successful scan', (tester) async {
      final prefs = MemoryPreferences();
      final bio = FakeBiometrics();
      await pumpApp(
        tester,
        familyBackend(),
        savedToken: 'tok',
        preferences: prefs,
        biometrics: bio,
      );
      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('fingerprintLockSwitch')));

      expect(bio.reasons, ['Confirm your fingerprint to lock Nurtura']);
      expect(prefs.values[AppLock.prefKey], 'on');
      expect(
        find.textContaining('will ask for your fingerprint'),
        findsOneWidget,
      );
      // Turning it on doesn't lock the app straight away.
      expect(find.byKey(const Key('lockScreen')), findsNothing);
    });

    testWidgets('stays off if the scan fails', (tester) async {
      final prefs = MemoryPreferences();
      await pumpApp(
        tester,
        familyBackend(),
        savedToken: 'tok',
        preferences: prefs,
        biometrics: FakeBiometrics(pass: false),
      );
      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('fingerprintLockSwitch')));

      expect(prefs.values.containsKey(AppLock.prefKey), isFalse);
      expect(find.text("Fingerprint lock wasn't turned on."), findsOneWidget);
    });
  });

  group('the lock screen', () {
    testWidgets('opens the app on a good fingerprint', (tester) async {
      final bio = FakeBiometrics();
      await pumpApp(
        tester,
        familyBackend(),
        savedToken: 'tok',
        preferences: lockedOn(),
        biometrics: bio,
      );
      // The prompt opens by itself and passes, so the app shows.
      expect(bio.reasons, ['Unlock Nurtura']);
      expect(find.byKey(const Key('lockScreen')), findsNothing);
      expect(find.byKey(const Key('tab_family')), findsOneWidget);
    });

    testWidgets('stays locked when the prompt is closed, and can try again', (
      tester,
    ) async {
      final bio = FakeBiometrics(pass: false);
      await pumpApp(
        tester,
        familyBackend(),
        savedToken: 'tok',
        preferences: lockedOn(),
        biometrics: bio,
      );
      expect(find.byKey(const Key('lockScreen')), findsOneWidget);
      expect(find.text('Nurtura is locked'), findsOneWidget);
      expect(find.byKey(const Key('tab_family')), findsNothing);

      bio.pass = true;
      await tapVisible(tester, find.byKey(const Key('unlockButton')));
      expect(find.byKey(const Key('lockScreen')), findsNothing);
    });

    testWidgets('explains a lockout', (tester) async {
      await pumpApp(
        tester,
        familyBackend(),
        savedToken: 'tok',
        preferences: lockedOn(),
        biometrics: FakeBiometrics(error: 'Too many tries.'),
      );
      expect(find.text('Too many tries.'), findsOneWidget);
    });

    testWidgets('"Use password instead" logs out and turns the lock off', (
      tester,
    ) async {
      final prefs = lockedOn();
      final backend = familyBackend();
      final store = await pumpApp(
        tester,
        backend,
        savedToken: 'tok',
        preferences: prefs,
        biometrics: FakeBiometrics(pass: false),
      );
      await tapVisible(tester, find.byKey(const Key('usePasswordInstead')));

      expect(find.byKey(const Key('emailField')), findsOneWidget);
      expect(store.token, isNull);
      expect(prefs.values.containsKey(AppLock.prefKey), isFalse);
      expect(backend.to('/api/auth/logout/'), hasLength(1));
    });

    testWidgets('never shows without a saved sign-in', (tester) async {
      await pumpApp(
        tester,
        FakeBackend((_) async => json({})),
        preferences: lockedOn(),
        biometrics: FakeBiometrics(pass: false),
      );
      expect(find.byKey(const Key('lockScreen')), findsNothing);
      expect(find.byKey(const Key('emailField')), findsOneWidget);
    });
  });

  group('locking again after time away', () {
    late DateTime now;
    late AppLock lock;

    setUp(() async {
      now = DateTime(2026, 10, 30, 9);
      lock = AppLock(FakeBiometrics(), lockedOn(), clock: () => now);
      await lock.load();
      await lock.unlock();
    });

    test('a minute or more away locks', () {
      lock.appLeft();
      now = now.add(AppLock.relockAfter);
      lock.appReturned();
      expect(lock.locked, isTrue);
    });

    test('a quick switch away does not', () {
      lock.appLeft();
      now = now.add(const Duration(seconds: 20));
      lock.appReturned();
      expect(lock.locked, isFalse);
    });

    test('nothing locks when the lock is off', () async {
      await lock.disable();
      lock.appLeft();
      now = now.add(const Duration(hours: 1));
      lock.appReturned();
      expect(lock.locked, isFalse);
    });
  });

  testWidgets('logging out turns the lock off for the next account', (
    tester,
  ) async {
    final prefs = MemoryPreferences();
    await pumpApp(
      tester,
      familyBackend(),
      savedToken: 'tok',
      preferences: prefs,
      biometrics: FakeBiometrics(),
    );
    await openFamily(tester);
    await tapVisible(tester, find.byKey(const Key('fingerprintLockSwitch')));
    expect(prefs.values[AppLock.prefKey], 'on');

    await tester.scrollUntilVisible(
      find.byKey(const Key('logoutButton')),
      200,
      scrollable: find.byType(Scrollable).last,
    );
    await tapVisible(tester, find.byKey(const Key('logoutButton')));
    expect(prefs.values.containsKey(AppLock.prefKey), isFalse);
  });
}
