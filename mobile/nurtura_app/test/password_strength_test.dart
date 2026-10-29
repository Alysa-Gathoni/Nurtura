import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nurtura_app/logic/password_strength.dart';

import 'helpers.dart';

List<bool> rulesMet(String password, {String email = ''}) => [
  for (final r in PasswordStrength.of(password, email: email).rules) r.met,
];

void main() {
  group('scoring (#140)', () {
    test('mirrors the backend rules', () {
      // Length, not only numbers, not like the email, not common.
      expect(rulesMet('abc'), [false, true, true, true]);
      expect(rulesMet('12345678'), [true, false, true, true]);
      expect(rulesMet('wanjiru2026', email: 'wanjiru@example.com'), [
        true,
        true,
        false,
        true,
      ]);
      expect(rulesMet('Password'), [true, true, true, false]);
    });

    test('breaking any rule is level 0, with the reason', () {
      expect(PasswordStrength.of('abc').level, 0);
      expect(PasswordStrength.of('abc').label, 'Too short');
      expect(PasswordStrength.of('12345678').label, 'Too weak');
    });

    test('length matters more than symbols', () {
      expect(PasswordStrength.of('mangotree').level, 1); // fair
      expect(PasswordStrength.of('mangotreeshade').level, 2); // 12+
      expect(PasswordStrength.of('mango tree in the shade').level, 3); // 16+
      // Mixed kinds help, but 8 characters is never strong on its own.
      expect(PasswordStrength.of('Mang0!ab').level, 2);
    });

    test('no composition rules: a long lowercase phrase is strong', () {
      final s = PasswordStrength.of('our baby loves the rain');
      expect(s.meetsRules, isTrue);
      expect(s.label, 'Strong');
    });
  });

  group('on the sign-in screen (#140)', () {
    testWidgets('greets per mode', (tester) async {
      await pumpApp(tester, FakeBackend((_) async => json({})));
      expect(find.text('Welcome back'), findsOneWidget);
      expect(find.byKey(const Key('authVillage')), findsOneWidget);

      await tester.tap(find.byKey(const Key('toggle_Register')));
      await tester.pumpAndSettle();
      expect(find.text('Join the village'), findsOneWidget);
      expect(find.text('Welcome back'), findsNothing);
    });

    testWidgets('the meter appears when registering, not when logging in', (
      tester,
    ) async {
      await pumpApp(tester, FakeBackend((_) async => json({})));
      await tester.enterText(find.byKey(const Key('passwordField')).last, 'x');
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('passwordStrength')), findsNothing);

      await tester.tap(find.byKey(const Key('toggle_Register')));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const Key('emailField')).last,
        'wanjiru@example.com',
      );
      await tester.enterText(
        find.byKey(const Key('passwordField')).last,
        'wanjiru1',
      );
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('passwordStrength')), findsOneWidget);
      expect(find.text('Too weak'), findsOneWidget);

      await tester.enterText(
        find.byKey(const Key('passwordField')).last,
        'mango tree in the shade',
      );
      await tester.pumpAndSettle();
      expect(find.text('Strong'), findsOneWidget);
    });
  });
}
