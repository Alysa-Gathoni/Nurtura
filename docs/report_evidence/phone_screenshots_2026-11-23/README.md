# Phone screenshots, 23 November 2026

Retakes of three screens whose earlier captures (12 and 16 November) showed the bottom navigation tab under its old name, **Today**. The tab has been **This week** since the weekly plan (#244). These replace the 12 and 16 November captures of the same screens: the child form, the milestone picker and the milestone tracker. With the 21 and 22 November sets, every caregiver screen in the report now comes from the final system.

| | |
|---|---|
| Date | 23 November 2026, 1:19–1:21 pm (EAT) |
| Phone | Samsung SM-A145F, Android 15, 1080 × 2408 (the same phone and resolution as the 22 November set), connected over USB |
| App | Debug build from `main` at `fa5c9f3` (after #277). The app code is the same as the 22 November build (`9f9a3c6`). |
| Backend | Django development server on the laptop, model warmed up, reached through `adb reverse tcp:8000 tcp:8000`, on a scratch copy of the development database (deleted afterwards). Sign-in codes were printed to the server console. |
| Data | Fictional only, the same as the 21 and 22 November sets: account `demo.caregiver@example.com`, child "Baby Amani" (born 16 Sep 2025, 14 months, concern Motor, interests animals and music), milestones recorded on 18 Nov 2026: "Walking with assistance" Achieved, "Tries to use things the right way, like a phone, cup, or book" Emerging, "Takes a few steps on their own" Not yet. Nothing was added, changed or saved during the captures. |
| Status bar | Do Not Disturb on; no notification icons show. Android's demo mode was requested (clock 12:00, full battery, full signal), but this Samsung phone ignored it, so the real time and a charging battery show. Demo mode was switched off afterwards. |
| Captured with | `adb exec-out screencap -p` |

## Files

| File | Screen | Replaces |
|---|---|---|
| `05a_child_form.png` | **Edit profile** for Baby Amani, filled in: name, Born, date of birth 16 Sep 2025, interests animals and music, Motor selected under "Areas you'd like support with", Save profile. The app opens this form as a full screen, so the bottom navigation bar isn't shown. | `07b_child_profile_concern.png` (16 Nov) |
| `05b_milestone_picker.png` | **Milestones → Record**: "steps" typed in the search field with the keyboard open, showing "Takes a few steps on their own" (Motor, by 15 months, CDC). The keyboard covers the bottom navigation bar on this screen. | `08_milestone_picker.png` (16 Nov) |
| `08a_milestone_tracker.png` | **Milestones → Tracker**, Moving: "Walking with assistance: Achieved at 14 months", "Takes a few steps on their own: Not yet · most often seen by 15 months", and the milestones not yet recorded or coming up. The bottom navigation bar shows **This week**, Explore, Progress, Milestones, Family. | `08b_tracker_moving.png` (16 Nov) |

## Checks

| Check | Result |
|---|---|
| Bottom navigation bar says "This week", not "Today", wherever it shows | Passed: it shows only in `08a_milestone_tracker.png`, and reads "This week" |
| No real personal data, emails, tokens or notification content | Passed: only the fictional child; no email shows on these screens |
| 1080 × 2408, the same as the 22 November set | Passed for all three |
