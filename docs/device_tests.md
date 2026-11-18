# Emulator device tests

> **Last updated: 2026-11-18** (#230). Every figure is from the runs on that day; each run's details and log are in [device_tests/](device_tests/).

The app had been run on one physical phone (Samsung SM-A145F, Android 15). These runs add the range Nurtura's users may have:
- the oldest Android the app supports, on a small screen;
- a current Android phone, at normal and at large text;
- a tablet.

Each run is the full end-to-end test (`integration_test/app_flow_test.dart`) against the real backend:
1. Register, with the emailed code typed automatically.
2. Agree to the privacy notice.
3. Log out and back in on the trusted phone.
4. Add a pregnancy profile and a child.
5. Record a milestone.
6. Get ranked recommendations with explanations.
7. Mark one done through the "Well done!" sheet, then rate it and comment.
8. Open Progress.
9. Switch the whole app to dark mode.

## Results

| Configuration | Android | Screen (px) | Density | Text scale | Result | Test time |
|---|---|---|---|---|---|---|
| Current phone | 17 (SDK 37) | 1080 × 2400 | 420 | 1.0 | **Passed** | 258 s |
| Small phone, oldest supported Android | 7.0 (SDK 24) | 720 × 1280 (360 × 640 dp) | 320 | default | **Passed** | 122 s |
| Current phone, large text | 17 (SDK 37) | 1080 × 2400 | 420 | 1.3 | **Passed** | 225 s |
| Tablet | 17 (SDK 37) | 2560 × 1600 | 320 | 1.0 | **Passed** | 356 s |

- **No layout overflow in any run.** None of the four logs contains "overflowed".
- **All four used the same test build,** with the fix in #237 (PR #240).

## What the runs found

| Finding | Fixed in |
|---|---|
| **App: on a 360 × 640 dp phone the milestone picker had no room for its list** ("A RenderFlex overflowed by 137 pixels on the bottom"), so no milestone could be chosen. This is a common size for budget Android phones. | #237 (PR #240): the picker's header, chips and list now scroll together |
| Test: it waited for the privacy checkbox at the end of a long list; on a phone the list doesn't build it until scrolled to | This PR (since #238 the agreement is also pinned in view) |
| Test: it expected the flow before the "Well done!" sheet (#185) | This PR: done → the sheet (interest, outcome) → Edit → rating and comment |
| Test: on small screens, the milestone search result, the Progress area grid and the dark-mode switch are below the fold | This PR: the test closes the keyboard and scrolls, as a person would |
| Tooling: the in-test screenshots never returned on a windowless emulator, and the run hung | This PR: `--dart-define=E2E_SCREENSHOTS=false` turns them off; phone runs keep them |

## How the runs work

- **Devices:** Android Studio emulators, no window, software graphics.
  - `Medium_Phone`: Android 17, 1080 × 2400.
  - `nurtura_api24_small`: "Galaxy Nexus" profile, Android 7.0, 720 × 1280.
  - `nurtura_tablet`: "Pixel Tablet" profile, Android 17, 2560 × 1600.
- **Backend:** the development server on the laptop, against a scratch copy of the database, with the console mailer, so sign-in codes are printed and not emailed. The emulator reaches it at `10.0.2.2:8000`, Android's address for the host computer, which `ALLOWED_HOSTS` must include.
- **The test app is built once,** with no emulator running, then installed on each device with `--use-application-binary`. Building beside a running emulator and the backend ran the 7.4 GB laptop out of memory and killed Gradle.
- **The emailed code** is read from the backend's log and typed with `adb` (`scripts/device_tests/type_code.py`). The helper checks the backend accepted it, and retries if the typing landed before the code screen was ready.
- **Before each run,** the test account `device-e2e@nurtura.invalid` is deleted from the scratch database (`reset_test_account.py`, which refuses any other database or email).

## Reproducing

From the repository root, with a scratch copy of the database (`backend\venv\Scripts\python.exe scripts\load_test\scratch_db.py create`) and the backend running against it, with `EMAIL_HOST` empty and `ALLOWED_HOSTS` including `10.0.2.2`, and its output in two logs:

1. **Build the test app once** (no emulator running), from `mobile/nurtura_app`:
   ```
   flutter build apk --debug -t integration_test/app_flow_test.dart --dart-define=API_BASE_URL=http://10.0.2.2:8000 --dart-define=E2E_EMAIL=device-e2e@nurtura.invalid --dart-define=E2E_SCREENSHOTS=false
   ```
2. **Run a configuration** (repeat with `nurtura_api24_small` / `nurtura_tablet`, or `-FontScale 1.3`):
   ```
   powershell -File scripts\device_tests\run_device_test.ps1 -Avd Medium_Phone -Label phone -Port 5560 -ServerLog <runserver stdout> -RequestLog <runserver stderr> -OutDir docs\device_tests\phone -Apk mobile\nurtura_app\build\app\outputs\flutter-apk\app-debug.apk
   ```

Each run writes `result.json` (the device's properties, timings, passed), the test log and the code helper's output.

## Limits

- **Emulators aren't real hardware.** Touch, performance and manufacturer changes to Android (for example Samsung's) are only covered by the one physical phone.
- **One run per configuration.** Timings vary between runs.
- **What isn't covered:**
  - Google sign-in, fingerprint log-in and offline use, which need a Google account, a fingerprint or a dropped network;
  - landscape: the app is portrait only (#214).
