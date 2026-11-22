# Mobile app, repository and reader test

> Generated 2026-11-21T23:26:03+03:00 at commit `45ea972` by `python scripts\report_evidence\mobile_and_repo.py`. Figures come from that run; UNKNOWN marks anything the script couldn't verify.

## 1h. Mobile app

Screens in `mobile/nurtura_app/lib/screens/` on `main` (every file on `main` is merged). First commit that added each file: `raw/mobile_screens.csv`.

| File | Widgets | Added (date, commit subject) |
|---|---|---|
| activity_detail_screen.dart | ActivityDetailScreen _Stars _DetailCard | 2026-10-10 feat: activity detail screen from a recommendation card (#84) |
| admin/admin_account_screen.dart | AdminAccountScreen | 2026-10-21 feat: administrator screens in the Flutter app (#123) |
| admin/admin_activities_screen.dart | AdminActivitiesScreen StatusPill _ActivityCard | 2026-10-21 feat: administrator screens in the Flutter app (#123) |
| admin/admin_activity_form_screen.dart | AdminActivityFormScreen _StatusPanel | 2026-10-21 feat: administrator screens in the Flutter app (#123) |
| admin/admin_dashboard_screen.dart | AdminDashboardScreen _Section _OverviewCard | 2026-10-21 feat: administrator screens in the Flutter app (#123) |
| admin/admin_feedback_screen.dart | AdminFeedbackScreen _FeedbackCard | 2026-10-21 feat: administrator screens in the Flutter app (#123) |
| admin/admin_shell.dart | AdminShell AdminHeader | 2026-10-21 feat: administrator screens in the Flutter app (#123) |
| auth_screen.dart | AuthScreen _FingerprintLogIn _OrDivider | 2026-10-01 feat: add Flutter registration/login screen wired to auth API (#23) |
| change_password_screen.dart | ChangePasswordScreen | 2026-10-29 feat: change password while signed in, for caregivers and admins (#142) |
| child_form_screen.dart | ChildFormScreen _DateField | 2026-10-01 feat: add child profile creation screen wired to backend (#24) |
| children_screen.dart | ChildrenScreen _ChildCard _DeleteAccountDialog | 2026-10-01 feat: add child profile creation screen wired to backend (#24) |
| explore_screen.dart | ExploreScreen _Heading _ActivityCard | 2026-11-09 feat: Explore tab to browse, search, save and try activities (#194) |
| forgot_password_screen.dart | ForgotPasswordScreen _StepDots | 2026-10-21 feat: reset a forgotten password with an emailed code (#126) |
| home_shell.dart | HomeShell | 2026-10-11 feat: modern, playful redesign with light and dark mode and a tabbed home (#90) |
| lock_screen.dart | LockScreen | 2026-10-29 feat: unlock the app with a fingerprint (#150) |
| milestone_screen.dart | MilestoneScreen _MilestoneTile _StatusChip | 2026-10-01 feat: add milestone recording screen wired to rule engine (#25) |
| milestone_tracker_screen.dart | MilestoneTrackerScreen _MilestoneCard _ObservationCard | 2026-11-09 feat: milestone tracker by area, with a weekly Nurtura observation (#192) |
| milestones_tab.dart | MilestonesTab | 2026-11-09 feat: milestone tracker by area, with a weekly Nurtura observation (#192) |
| privacy_notice_screen.dart | PrivacyNoticeScreen | 2026-10-26 feat: privacy notice and consent before adding a child's data (#136) |
| progress_screen.dart | ProgressScreen _SectionTitle _Hero | 2026-10-11 feat: modern, playful redesign with light and dark mode and a tabbed home (#90) |
| recommendations_screen.dart | RecommendationsScreen RecommendationCard ReferralNotice | 2026-10-10 feat: recommendations screen for the selected child (#82) |
| verify_code_screen.dart | VerifyCodeScreen CodeBoxes | 2026-10-11 feat: two-step verification code screen in the app (#91) |

**Offline cache** (`mobile/nurtura_app/lib/state/recommendation_cache.dart`):

- line 7: /// The last recommendation batch per child, kept on the device so it can
- line 8: /// be shown offline (offline use, a SOFIA addition). Cleared whenever the user signs out or the
- line 9: /// session ends, so another account on the same phone never sees it.
- line 14: /// Forgets one child's batch (the child was deleted).
- line 19: /// A cached batch and when it was saved on this device.
- line 27: /// [RecommendationCache] in the app's shared preferences.
- line 29: static const _prefix = 'nurtura.recommendations.child.';
- line 35: final raw = (await _prefs).getString('$_prefix$childId');
- line 51: '$_prefix$childId',
- line 61: (await _prefs).remove('$_prefix$childId');
- line 66: for (final key in prefs.getKeys().where((k) => k.startsWith(_prefix))) {
- line 72: /// In-memory cache for tests.

**Launching offline:** covered by these widget tests:

- mobile/nurtura_app/test/offline_launch_test.dart:45: testWidgets('opened offline, the saved session and ideas are still there', (
- mobile/nurtura_app/test/offline_launch_test.dart:71: testWidgets('offline with nothing saved: still signed in, with a retry', (
- mobile/nurtura_app/test/offline_launch_test.dart:86: testWidgets('an ended session (401) still signs out and forgets the list', (
- mobile/nurtura_app/test/offline_launch_test.dart:106: testWidgets('logging out forgets the saved list', (tester) async {
- mobile/nurtura_app/test/offline_recommendations_test.dart:13: testWidgets('a batch from the server is saved on the device', (tester) async {
- mobile/nurtura_app/test/offline_recommendations_test.dart:26: testWidgets('offline, the saved batch is shown with a notice', (
- mobile/nurtura_app/test/offline_recommendations_test.dart:49: testWidgets('offline with nothing saved shows the error and a retry', (
- mobile/nurtura_app/test/offline_recommendations_test.dart:61: testWidgets('a server answer (404) never falls back to the saved batch', (
- mobile/nurtura_app/test/offline_recommendations_test.dart:78: testWidgets('a 401 clears what was saved', (tester) async {
- mobile/nurtura_app/test/offline_recommendations_test.dart:96: testWidgets('logging out clears what was saved', (tester) async {

**"Activity ideas, not a medical check" footer:** not found in `mobile/nurtura_app/lib` (searched: "not a medical", "medical check", "ideas, not", "health check", "footer", case-insensitive). Treat it as not built.

**Screenshots in the repository:** 21 files:

- `docs/evidence/e2e_2026-10-15/01_login.png`
- `docs/evidence/e2e_2026-10-15/02_register.png`
- `docs/evidence/e2e_2026-10-15/03_code_screen.png`
- `docs/evidence/e2e_2026-10-15/04_no_children_yet.png`
- `docs/evidence/e2e_2026-10-15/05_expecting_form.png`
- `docs/evidence/e2e_2026-10-15/06_expecting_milestones_message.png`
- `docs/evidence/e2e_2026-10-15/07_child_form.png`
- `docs/evidence/e2e_2026-10-15/08_milestone_picker.png`
- `docs/evidence/e2e_2026-10-15/09_status_selected.png`
- `docs/evidence/e2e_2026-10-15/10_milestone_recorded.png`
- `docs/evidence/e2e_2026-10-15/11_recommendations.png`
- `docs/evidence/e2e_2026-10-15/12_activity_detail.png`
- `docs/evidence/e2e_2026-10-15/13_done_and_feedback.png`
- `docs/evidence/e2e_2026-10-15/14_card_done_and_rated.png`
- `docs/evidence/e2e_2026-10-15/15_progress.png`
- `docs/evidence/e2e_2026-10-15/16_today_dark.png`
- `docs/report_evidence/figures/alpha_curve.png`
- `docs/report_evidence/figures/grade_distribution.png`
- `docs/report_evidence/figures/per_profile_test_ndcg5.png`
- `docs/report_evidence/figures/published_heatmap.png`
- `docs/report_evidence/figures/rank_grade_matrix.png`

## 1i. Repository

| Item | Value | How |
|---|---|---|
| URL | https://github.com/Alysa-Gathoni/Nurtura | `gh repo view` |
| Default branch | main | `gh repo view` |
| Tags | pre-weekly-plan 2026-11-20, sprint5-eval-v1 2026-10-10, sprint6-explanations-v1 2026-10-10, sprint9-eval-v2 2026-11-02, sprint9-eval-v3 2026-11-21, sprint9-eval-v3.1 2026-11-21 | `git tag` |
| Merged pull requests | 132 | `gh pr list --state merged` |
| Closed issues | 132 | `gh issue list --state closed` |
| Commits on main | 328 | `git rev-list --count origin/main` |
| CI runs (completed, last 304) | {'success': 299, 'failure': 5}; pass rate 98.4% | `gh run list` |
| Contributors (GitHub) | 1 (logins redacted; contributions: [324]) | `gh api repos/.../contributors` |

Milestones (`raw/milestones_github.csv`). Milestones are set on issues; a merged PR counts towards its own milestone or, if it has none, the milestone of the issue it closes. Commits are those in those PRs. No milestone has been closed on GitHub, so there are no close dates.

| Milestone | State | Created | Closed | Closed issues | Merged PRs | Commits in merged PRs |
|---|---|---|---|---|---|---|
| Sprint 2: Core Data Layer | open | 2026-09-29 | open | 7 | 7 | 9 |
| Sprint 3: Rule Engine | open | 2026-09-29 | open | 3 | 3 | 4 |
| Sprint 4: Semantic Retrieval | open | 2026-09-29 | open | 4 | 5 | 10 |
| Sprint 5: Weighted Ranking | open | 2026-09-29 | open | 8 | 8 | 12 |
| Sprint 6: Explainability | open | 2026-09-29 | open | 14 | 14 | 26 |
| Sprint 7: Feedback & History | open | 2026-09-29 | open | 3 | 3 | 3 |
| Sprint 8: Mobile App | open | 2026-09-29 | open | 27 | 27 | 37 |
| Sprint 9: Evaluation | open | 2026-09-29 | open | 57 | 56 | 77 |
| Sprint 10: Documentation | open | 2026-09-29 | open | 5 | 5 | 7 |
| Sprint 3.5: Minimal Mobile Shell | open | 2026-10-01 | open | 3 | 3 | 6 |
| (no milestone) |  |  |  | 1 | 1 | 1 |

## 1j. Reader-test and questionnaire outputs

Files whose names mention reader, questionnaire, response or scoring: `backend/recommendations/test_reader_test_scripts.py`, `docs/explanation_reader_test.md`, `docs/explanation_reader_test_cards.md`, `docs/explanation_reader_test_form.md`, `docs/explanation_reader_test_session_sheet.md`, `scripts/caregiver_questionnaire_form.gs`, `scripts/reader_test_forms.gs`, `scripts/score_caregiver_questionnaire.py`, `scripts/score_reader_test.py`.

Exported responses or scorer output (CSV, JSON, XLSX or TXT among them): none. **UNKNOWN**: no reader-test responses or scorer output are in the repository (the test and the caregiver sessions have not been run, or their exports were kept out of git).
