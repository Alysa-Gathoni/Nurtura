// End-to-end run of the Sprint 8 round trip against the real Django backend:
// register, profiles, a milestone, ranked recommendations with
// explanations, mark done and feedback (#104).
//
// Needs the backend running (python manage.py runserver). On a phone over
// USB (adb reverse tcp:8000 tcp:8000), from mobile/nurtura_app:
//   flutter drive -d <device id> \
//     --driver=test_driver/integration_test.dart \
//     --target=integration_test/app_flow_test.dart \
//     --dart-define=API_BASE_URL=http://127.0.0.1:8000 \
//     --dart-define=E2E_EMAIL=someone-new@example.com
// or in Chrome with ChromeDriver on port 4444 (-d chrome).
// Screenshots are saved to build/e2e_screenshots/.
//
// Registering emails a sign-in code (#91). With the console mailer the code
// is printed by runserver; type it into the app within three minutes.

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:nurtura_app/config.dart';
import 'package:nurtura_app/main.dart';
import 'package:nurtura_app/services/api_client.dart';
import 'package:nurtura_app/state/device_id_store.dart';
import 'package:nurtura_app/state/preferences.dart';
import 'package:nurtura_app/state/recommendation_cache.dart';
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

/// Pumps frames until [finder] matches nothing (e.g. a snackbar has gone).
Future<void> pumpUntilGone(
  WidgetTester tester,
  Finder finder, {
  Duration timeout = const Duration(seconds: 15),
}) async {
  final end = DateTime.now().add(timeout);
  while (DateTime.now().isBefore(end)) {
    if (finder.evaluate().isEmpty) return;
    await tester.pump(const Duration(milliseconds: 100));
  }
  throw TestFailure('Timed out waiting for $finder to go away');
}

Future<void> tap(WidgetTester tester, Finder finder) async {
  await pumpUntil(tester, finder);
  // On a phone the keyboard stays up after typing and squeezes the screen,
  // so close it first or the tap can land on something else.
  if (FocusManager.instance.primaryFocus?.hasFocus ?? false) {
    FocusManager.instance.primaryFocus!.unfocus();
    await tester.pump(const Duration(milliseconds: 600));
  }
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

/// Scrolls the activity screen until [finder] is built, then taps it.
Future<void> tapOnDetail(WidgetTester tester, Finder finder) async {
  await tester.scrollUntilVisible(
    finder,
    200,
    scrollable: find
        .descendant(
          of: find.byKey(const Key('activityDetail')),
          matching: find.byType(Scrollable),
        )
        .first,
  );
  await tap(tester, finder);
}

Finder keyStartingWith(String prefix) => find.byWidgetPredicate(
  (w) =>
      w.key is ValueKey<String> &&
      (w.key! as ValueKey<String>).value.startsWith(prefix),
);

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  // A tap that misses its target fails the run there, not several steps on.
  WidgetController.hitTestWarningShouldBeFatal = true;

  late WidgetTester tester;

  // On Android the app's surface must be turned into an image once before
  // screenshots can be taken; the web needs nothing.
  var surfaceConverted = kIsWeb;

  // Once converted, the phone's screen stops updating live, so the tester
  // couldn't see the code they type. On Android, screenshots therefore
  // start only after the code step (the earlier screens are skipped).
  var humanStepsDone = kIsWeb;

  Future<void> screenshot(String name) async {
    if (!humanStepsDone) {
      debugPrint('Screenshot $name skipped: the tester still has to type');
      return;
    }
    if (!surfaceConverted) {
      await binding.convertFlutterSurfaceToImage();
      surfaceConverted = true;
    }
    // The capture waits for a new frame, and in a test frames are drawn
    // only when pumped: keep pumping until it's done.
    var done = false;
    final shot = binding.takeScreenshot(name).whenComplete(() => done = true);
    while (!done) {
      await tester.pump(const Duration(milliseconds: 100));
    }
    await shot;
  }

  testWidgets('the Sprint 8 round trip on the real backend', (t) async {
    tester = t;
    expect(email, isNotEmpty, reason: 'pass --dart-define=E2E_EMAIL=...');

    await tester.pumpWidget(
      NurturaApp(
        api: ApiClient(baseUrl: apiBaseUrl),
        // In memory, so the run starts signed out and leaves the phone's
        // saved session alone.
        tokenStore: MemoryTokenStore(),
        recommendationCache: MemoryRecommendationCache(),
        preferences: MemoryPreferences(),
        deviceIds: MemoryDeviceIdStore(),
      ),
    );
    await pumpUntil(tester, find.byKey(const Key('emailField')));
    await screenshot('01_login');

    // 1. Register; the emailed code is typed by the tester.
    await tap(tester, find.byKey(const Key('toggle_Register')));
    await type(tester, 'emailField', email);
    await type(tester, 'passwordField', password);
    await type(tester, 'confirmField', password);
    await screenshot('02_register');
    await tap(tester, find.byKey(const Key('submitButton')));
    await pumpUntil(tester, find.byKey(const Key('codeField')));
    await screenshot('03_code_screen');
    await pumpUntil(
      tester,
      find.byKey(const Key('privacyAgreeCheckbox')),
      timeout: const Duration(minutes: 3),
    );
    humanStepsDone = true;

    // A new caregiver agrees to the privacy notice before anything else
    // (#136); it isn't asked again at the next login.
    await screenshot('04a_privacy_notice');
    await tap(tester, find.byKey(const Key('privacyAgreeCheckbox')));
    await tap(tester, find.byKey(const Key('privacyAgreeButton')));
    await pumpUntil(tester, find.text('Add your first child'));
    await screenshot('04_no_children_yet');

    // 2. Log out and back in: this phone is now trusted, so no code.
    await tap(tester, find.byKey(const Key('logoutButton')));
    await type(tester, 'emailField', email);
    await type(tester, 'passwordField', password);
    await tap(tester, find.byKey(const Key('submitButton')));
    await pumpUntil(tester, find.text('Add your first child'));
    expect(find.byKey(const Key('codeField')), findsNothing);

    // 3. An expecting (prenatal) profile with a Sensory concern.
    await tap(tester, find.byKey(const Key('addChildButton')));
    await type(tester, 'childNameField', 'Baby E2E');
    await tap(tester, find.byKey(const Key('toggle_Expecting')));
    await tap(tester, find.byKey(const Key('dateField')));
    await tap(tester, find.text('OK'));
    await tap(tester, find.byKey(const Key('concern_Sensory')));
    await screenshot('05_expecting_form');
    await tap(tester, find.byKey(const Key('saveChildButton')));
    await pumpUntil(tester, find.byKey(const Key('prenatalMessage')));
    await screenshot('06_expecting_milestones_message');

    // 4. A child born about six months ago (the picker's default), added
    // from the Family tab; saving opens Milestones for that child.
    await tap(tester, find.byKey(const Key('tab_family')));
    await pumpUntil(tester, find.text('Baby E2E'));
    await tap(tester, find.byKey(const Key('addChildButton')));
    await type(tester, 'childNameField', 'Amani E2E');
    await tap(tester, find.byKey(const Key('dateField')));
    await tap(tester, find.text('OK'));
    await type(tester, 'interestField', 'music');
    await tap(tester, find.byKey(const Key('addInterestButton')));
    await screenshot('07_child_form');
    await tap(tester, find.byKey(const Key('saveChildButton')));
    await pumpUntil(tester, find.byKey(const Key('milestoneSearchField')));
    await pumpUntil(tester, keyStartingWith('milestone_'));
    await screenshot('08_milestone_picker');

    // 5. Search the catalogue and record a due milestone as Not yet.
    await type(tester, 'milestoneSearchField', 'cooing');
    await pumpUntil(tester, find.byKey(const Key('milestone_CDC-04M-LA-01')));
    await tester.pump(const Duration(milliseconds: 500));
    await tap(tester, find.byKey(const Key('milestone_CDC-04M-LA-01')));
    await tap(tester, find.byKey(const Key('status_not_yet')));
    await screenshot('09_status_selected');
    await tap(tester, find.byKey(const Key('saveMilestoneButton')));
    await pumpUntil(tester, find.byKey(const Key('milestoneRecorded')));
    expect(find.byKey(const Key('profileUpdated')), findsOneWidget);
    await screenshot('10_milestone_recorded');

    // 6. Ranked recommendations with explanations, on Today.
    await tap(tester, find.byKey(const Key('seeRecommendationsButton')));
    await pumpUntil(
      tester,
      keyStartingWith('recommendation_'),
      timeout: const Duration(seconds: 90), // the AI model may be loading
    );
    expect(find.byKey(const Key('explanationBox')), findsWidgets);
    await screenshot('11_recommendations');

    // 7. Open one, mark it done and leave feedback.
    await tap(tester, keyStartingWith('recommendation_').first);
    await pumpUntil(tester, find.byKey(const Key('activityDetail')));
    await screenshot('12_activity_detail');
    await tapOnDetail(tester, find.byKey(const Key('markDoneButton')));
    await pumpUntil(tester, find.byKey(const Key('doneStatus')));
    // The "Well done!" message covers the bottom of the screen for a few
    // seconds; a caregiver would wait for it too.
    await pumpUntilGone(tester, find.byType(SnackBar));
    await tapOnDetail(tester, find.byKey(const Key('star_4')));
    await type(tester, 'feedbackComment', 'Lots of smiles. (E2E test)');
    await tapOnDetail(tester, find.byKey(const Key('sendFeedbackButton')));
    await pumpUntil(tester, find.text('Thanks for your feedback!'));
    await screenshot('13_done_and_feedback');

    await tester.pageBack();
    await pumpUntil(tester, keyStartingWith('doneChip_'));
    await tester.pump(const Duration(milliseconds: 800)); // finish the slide
    expect(keyStartingWith('ratingChip_'), findsOneWidget);
    await screenshot('14_card_done_and_rated');

    // 8. Progress, then the whole app in dark mode.
    await tap(tester, find.byKey(const Key('tab_progress')));
    await pumpUntil(tester, find.byKey(const Key('area_Language')));
    await screenshot('15_progress');
    await tap(tester, find.byKey(const Key('tab_family')));
    await tap(tester, find.byKey(const Key('toggle_Dark')));
    await tap(tester, find.byKey(const Key('tab_today')));
    await pumpUntil(tester, keyStartingWith('recommendation_'));
    await screenshot('16_today_dark');
  });
}
