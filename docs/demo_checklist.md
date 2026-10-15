# Live demo checklist

A short guide for showing Nurtura working on a phone against the backend on a laptop, as in the progress review. Commands are for Windows PowerShell, from the repository root.

## The day before

- [ ] Merge the open pull requests, then `git pull` on `main`.
- [ ] **Reinstall the normal app on the phone.** Running the end-to-end test (`flutter drive`) replaces it with a test build. Steps 3–4 below reinstall it.
- [ ] **Prepare a demo account:** register on the phone, type the emailed code, and leave "Trust this phone for 30 days" on. On the day, logging in then needs no code, so the demo doesn't depend on email arriving quickly.
- [ ] Charge the phone and keep its USB cable with the laptop.
- [ ] Keep the backup evidence to hand: [`docs/evidence/e2e_2026-10-15/`](evidence/e2e_2026-10-15/) (16 screenshots) and [`testing_and_evaluation_record.md`](testing_and_evaluation_record.md).

## Setting up (about 5 minutes)

1. **PostgreSQL** must be running: Windows Services → `postgresql-x64-18` → Running.
2. **Backend:**
   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   $env:NURTURA_MODEL_WARMUP = "1"   # loads the AI model at start-up, so the first ideas come quickly
   python manage.py runserver 127.0.0.1:8000
   ```
   Leave this window open. Sign-in codes and any errors appear here.
3. **Phone:** unlock it, connect it by USB with USB debugging on, then in a second window:
   ```powershell
   adb devices                      # the phone should be listed as "device"
   adb reverse tcp:8000 tcp:8000    # lets the phone reach the laptop's backend
   ```
   Run `adb reverse` again whenever the cable is unplugged and plugged back in.
4. **App:**
   ```powershell
   cd mobile\nurtura_app
   flutter run -d <device id> --dart-define=API_BASE_URL=http://127.0.0.1:8000
   ```
   `flutter devices` shows the device ID.

## If there's no internet at the venue

Sign-in codes are emailed, so they need internet. Without it:

1. In `backend\.env`, empty the email host: `EMAIL_HOST=`.
2. Restart the backend (Ctrl+C, then `python manage.py runserver 127.0.0.1:8000`).
3. Codes are now printed in the backend window instead of emailed.

A prepared demo account on a trusted phone (see "The day before") needs no code at all. Put `EMAIL_HOST` back afterwards.

## What to show (about 5 minutes)

1. **Sign in** on the trusted phone: no code needed. Mention that a new phone gets an emailed code.
2. **Family → Add a child:** a child of a few months, with an interest.
3. **Milestones:** search a milestone that's due, e.g. "cooing", and record **Not yet**. Point out "developmental profile was updated" (the rule engine).
4. **See ideas:** the ranked activities (the rule engine, SBERT similarity and the weighted ranking).
5. **Open the top activity:** "Why this?" explains the reason in plain language.
6. **Done!** and a **star rating** with a comment; back on Today the card shows Done and the rating.
7. **Progress:** the child's own records and the streak, with no comparison to other children.
8. **Admin** (on the laptop, `http://127.0.0.1:8000/admin/`, with an administrator account): Feedback shows the rating against the activity, without the child's name or the caregiver's email.

## If something goes wrong

| Problem | Fix |
|---|---|
| "Can't reach the Nurtura server" | Check the backend window is running; run `adb reverse tcp:8000 tcp:8000` again |
| No code email | Check Spam; or use the no-internet steps above |
| The first ideas take a while | The AI model is loading; the app allows for it. Start the backend with `NURTURA_MODEL_WARMUP=1` to avoid it |
| The phone isn't listed by `adb devices` | Unlock it, re-plug the cable, and accept the "Allow USB debugging" prompt |
| Anything else | Show the screenshots in `docs/evidence/e2e_2026-10-15/` and the testing record |
