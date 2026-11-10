# Nurtura app

The Android app for Nurtura: developmental activity ideas for caregivers, from pregnancy to 36 months. It talks to the Django backend in [`../../backend`](../../backend). The project README covers the whole system: [../../README.md](../../README.md).

## What's in it

| Tab or screen | What the caregiver does |
|---|---|
| Today | Sees five suggested activities with plain-language reasons, marks them done and says how they went |
| Explore | Browses, searches and saves activities |
| Progress | Sees the child's own history, never compared with other children |
| Milestones | Records milestones by area and reads the weekly Nurtura observation |
| Family | Adds, edits and deletes children; account and privacy settings |
| Admin screens | Administrators manage activities and read feedback |

Code layout under `lib/`:

| Folder | Holds |
|---|---|
| `screens/` | One file per screen; `screens/admin/` for administrators |
| `services/` | Calls to the REST API |
| `models/` | Models for API responses |
| `state/` | App state: sign-in, children, recommendations saved for offline use |
| `logic/` | Pure functions, such as the progress summary |
| `widgets/`, `theme/`, `utils/` | Shared UI pieces, light and dark themes, helpers |
| `config.dart` | The backend address and Google client ID, set at build time |

## Running it

You need Flutter 3.47.4 (the version CI uses) and the backend running (see the project README).

```bash
flutter pub get
flutter run -d <device-id> --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

- **Phone over USB:** run `adb reverse tcp:8000 tcp:8000` first, so the phone reaches the laptop's backend at `127.0.0.1`.
- **Android emulator:** leave out `API_BASE_URL`; the app uses `http://10.0.2.2:8000`.
- **Google sign-in:** add `--dart-define=GOOGLE_SERVER_CLIENT_ID=<web client ID>`.

## Checks

```bash
flutter analyze
flutter test
```

The end-to-end test (`integration_test/app_flow_test.dart`) runs on a phone against a real backend and needs a person to type the emailed sign-in code; see the project README.

Only Android is supported.
