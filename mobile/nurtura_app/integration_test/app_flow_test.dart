// End-to-end run of the Sprint 3.5 flow against the real Django backend.
//
// Needs the backend running (python manage.py runserver) and ChromeDriver on
// port 4444, then from mobile/nurtura_app:
//   flutter drive -d chrome \
//     --driver=test_driver/integration_test.dart \
//     --target=integration_test/app_flow_test.dart \
//     --dart-define=E2E_EMAIL=someone-new@example.com
// Screenshots are saved to build/e2e_screenshots/.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:nurtura_app/config.dart';
import 'package:nurtura_app/main.dart';
import 'package:nurtura_app/services/api_client.dart';
import 'package:nurtura_app/state/token_store.dart';

const email = String.fromEnvironment('E2E_EMAIL');
const password = String.fromEnvironment(
  'E2E_PASSWORD',
  defaultValue: 'Nurtura-E2E-pass-2026',
);

/// Pumps frames until [finder] matches; real network calls take time and
/// spinners never settle, so pumpAndSettle can't be used.
Future<void> pumpUntil(
  WidgetTester tester,
  Finder finder, {
  Duration timeout = const Duration(seconds: 40),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    await tester.pump(const Duration(milliseconds: 100));
    if (finder.evaluate().isNotEmpty) return;
  }
  throw TestFailure('Timed out waiting for $finder');
}

Future<void> tap(WidgetTester tester, Finder finder) async {
  await pumpUntil(tester, finder);
  await tester.ensureVisible(finder);
  await tester.pump(const Duration(milliseconds: 300));
  await tester.tap(finder);
  await tester.pump(const Duration(milliseconds: 300));
}

Future<void> type(WidgetTester tester, String key, String text) async {
  // Wait for the field to exist first: `.last` throws while it doesn't.
  await pumpUntil(tester, find.byKey(Key(key)));
  await tester.enterText(find.byKey(Key(key)).last, text);
  await tester.pump(const Duration(milliseconds: 200));
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  Future<void> screenshot(String name) async {
    await binding.takeScreenshot(name);
  }

  testWidgets('register, log in, create profiles and record a milestone', (
    tester,
  ) async {
    expect(email, isNotEmpty, reason: 'pass --dart-define=E2E_EMAIL=...');

    await tester.pumpWidget(
      NurturaApp(
        api: ApiClient(baseUrl: apiBaseUrl),
        tokenStore: SecureTokenStore(),
      ),
    );
    await pumpUntil(tester, find.byKey(const Key('emailField')));
    await screenshot('01_login');

    // 1. Register a new caregiver.
    await tap(tester, find.byKey(const Key('toggle_Register')));
    await type(tester, 'emailField', email);
    await type(tester, 'passwordField', password);
    await type(tester, 'confirmField', password);
    await screenshot('02_register');
    await tap(tester, find.byKey(const Key('submitButton')));
    await pumpUntil(tester, find.text('Add your first child'));
    await screenshot('03_registered_empty_children');

    // 2. Log out, then log back in with the same account.
    await tap(tester, find.byKey(const Key('logoutButton')));
    await pumpUntil(tester, find.byKey(const Key('emailField')));
    await type(tester, 'emailField', email);
    await type(tester, 'passwordField', password);
    await tap(tester, find.byKey(const Key('submitButton')));
    await pumpUntil(tester, find.text('Add your first child'));

    // 3. An expecting (prenatal) profile with a Sensory concern.
    await tap(tester, find.byKey(const Key('addChildButton')));
    await type(tester, 'childNameField', 'Baby E2E');
    await tap(tester, find.byKey(const Key('toggle_Expecting')));
    await tap(tester, find.byKey(const Key('dateField')));
    await tap(tester, find.text('OK'));
    await tap(tester, find.byKey(const Key('concern_Sensory')));
    await screenshot('04_expecting_form');
    await tap(tester, find.byKey(const Key('saveChildButton')));
    await pumpUntil(tester, find.byKey(const Key('prenatalMessage')));
    await screenshot('05_expecting_milestones_message');
    await tap(tester, find.byTooltip('Back'));
    await pumpUntil(tester, find.text('Baby E2E'));

    // 4. A child born about six months ago (the picker's default).
    await tap(tester, find.byKey(const Key('addChildButton')));
    await type(tester, 'childNameField', 'Amani E2E');
    await tap(tester, find.byKey(const Key('dateField')));
    await tap(tester, find.text('OK'));
    await type(tester, 'interestField', 'music');
    await tap(tester, find.byKey(const Key('addInterestButton')));
    await screenshot('06_child_form');
    await tap(tester, find.byKey(const Key('saveChildButton')));
    await pumpUntil(tester, find.byKey(const Key('milestoneSearchField')));
    await pumpUntil(
      tester,
      find.byWidgetPredicate(
        (w) =>
            w.key is ValueKey<String> &&
            (w.key! as ValueKey<String>).value.startsWith('milestone_'),
      ),
    );
    await screenshot('07_milestone_picker');

    // 5. Search the catalogue and record a due milestone as Not yet.
    await type(tester, 'milestoneSearchField', 'cooing');
    await pumpUntil(tester, find.byKey(const Key('milestone_CDC-04M-LA-01')));
    await tester.pump(const Duration(milliseconds: 500));
    await screenshot('08_search_results');
    await tap(tester, find.byKey(const Key('milestone_CDC-04M-LA-01')));
    await tap(tester, find.byKey(const Key('status_not_yet')));
    await screenshot('09_status_selected');
    await tap(tester, find.byKey(const Key('saveMilestoneButton')));
    await pumpUntil(tester, find.byKey(const Key('milestoneRecorded')));
    expect(find.byKey(const Key('profileUpdated')), findsOneWidget);
    await screenshot('10_milestone_recorded');
  });
}
