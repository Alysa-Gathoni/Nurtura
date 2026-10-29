import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:nurtura_app/models/app_user.dart';

import 'admin_test.dart' show adminBackend, adminJson, pumpAdmin;
import 'edit_and_delete_test.dart'
    show backendWith, body, childJson, openFamily, tapVisible;
import 'helpers.dart';

// Changing the password while signed in (#142).

const newPassword = 'mango tree in the shade';

Future<void> fillAndSave(
  WidgetTester tester, {
  String current = 'old-password',
  String password = newPassword,
  String? confirm,
}) async {
  await tester.enterText(
    find.byKey(const Key('currentPasswordField')).last,
    current,
  );
  await tester.enterText(
    find.byKey(const Key('newPasswordField')).last,
    password,
  );
  await tester.enterText(
    find.byKey(const Key('confirmNewPasswordField')).last,
    confirm ?? password,
  );
  await tapVisible(tester, find.byKey(const Key('savePasswordButton')));
}

void main() {
  setUpAll(() => WidgetController.hitTestWarningShouldBeFatal = true);

  test('has_password is read, and missing means true', () {
    expect(
      AppUser.fromJson({'id': 1, 'has_password': false}).hasPassword,
      isFalse,
    );
    expect(AppUser.fromJson({'id': 1}).hasPassword, isTrue);
  });

  group('a caregiver', () {
    testWidgets('changes it from Family and keeps the new token', (
      tester,
    ) async {
      http.Request? sent;
      final backend = backendWith((r) async {
        if (r.url.path == '/api/auth/password/') {
          sent = r;
          return json({'token': 'tok-new', 'user': caregiverJson});
        }
        return null;
      }, children: [childJson()]);
      final store = await pumpApp(tester, backend, savedToken: 'tok');
      await openFamily(tester);

      expect(find.text('Change password'), findsOneWidget);
      await tapVisible(tester, find.byKey(const Key('passwordSettingsButton')));
      expect(find.text('For wanjiru@example.com'), findsOneWidget);

      await fillAndSave(tester);
      expect(body(sent!), {
        'current_password': 'old-password',
        'new_password': newPassword,
        // So this phone keeps fingerprint log-in (#150).
        'device_id': testDeviceId,
      });
      expect(store.token, 'tok-new');
      expect(find.byKey(const Key('currentPasswordField')), findsNothing);
      expect(find.textContaining('Password changed'), findsOneWidget);
    });

    testWidgets('a wrong current password shows under that field', (
      tester,
    ) async {
      final backend = backendWith((r) async {
        if (r.url.path == '/api/auth/password/') {
          return json({
            'current_password': ["That password isn't right."],
          }, 400);
        }
        return null;
      }, children: [childJson()]);
      final store = await pumpApp(tester, backend, savedToken: 'tok');
      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('passwordSettingsButton')));
      await fillAndSave(tester, current: 'wrong');

      expect(find.text("That password isn't right."), findsOneWidget);
      expect(store.token, 'tok');
    });

    testWidgets('mismatched passwords are caught before sending', (
      tester,
    ) async {
      final backend = backendWith((r) async => null, children: [childJson()]);
      await pumpApp(tester, backend, savedToken: 'tok');
      await openFamily(tester);
      await tapVisible(tester, find.byKey(const Key('passwordSettingsButton')));
      await fillAndSave(tester, confirm: 'something else');

      expect(find.text("Passwords don't match."), findsOneWidget);
      expect(backend.to('/api/auth/password/'), isEmpty);
    });

    testWidgets('an account made with Google sets one with a code', (
      tester,
    ) async {
      final backend = backendWith((r) async {
        if (r.url.path == '/api/auth/me/') {
          return json({...caregiverJson, 'has_password': false});
        }
        return null;
      }, children: [childJson()]);
      await pumpApp(tester, backend, savedToken: 'tok');
      await openFamily(tester);

      expect(find.text('Set a password'), findsOneWidget);
      await tapVisible(tester, find.byKey(const Key('passwordSettingsButton')));
      expect(find.text('Set a password'), findsOneWidget);
      final email = tester.widget<EditableText>(
        find.descendant(
          of: find.byKey(const Key('resetEmailField')),
          matching: find.byType(EditableText),
        ),
      );
      expect(email.controller.text, 'wanjiru@example.com');
      expect(email.readOnly, isTrue);
    });
  });

  testWidgets('the strength meter checks the new password (#147)', (
    tester,
  ) async {
    final backend = backendWith((r) async => null, children: [childJson()]);
    await pumpApp(tester, backend, savedToken: 'tok');
    await openFamily(tester);
    await tapVisible(tester, find.byKey(const Key('passwordSettingsButton')));

    await tester.enterText(
      find.byKey(const Key('newPasswordField')).last,
      'wanjiru2026',
    );
    await tester.pumpAndSettle();
    // Like the account's email (wanjiru@example.com), so not accepted.
    expect(find.text('Too weak'), findsOneWidget);

    await tester.enterText(
      find.byKey(const Key('newPasswordField')).last,
      newPassword,
    );
    await tester.pumpAndSettle();
    expect(find.text('Strong'), findsOneWidget);
  });

  testWidgets('an administrator changes it from the Account tab', (
    tester,
  ) async {
    http.Request? sent;
    final backend = adminBackend(
      handler: (r) async {
        if (r.url.path == '/api/auth/password/') {
          sent = r;
          return json({'token': 'tok-admin-new', 'user': adminJson});
        }
        return null;
      },
    );
    await pumpAdmin(tester, backend);
    await tapVisible(tester, find.byKey(const Key('admin_tab_account')));
    await tapVisible(tester, find.byKey(const Key('passwordSettingsButton')));
    await fillAndSave(tester);

    expect(sent, isNotNull);
    expect(find.byKey(const Key('admin_tab_account')), findsOneWidget);
  });
}
