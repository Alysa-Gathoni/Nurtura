import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/privacy_notice.dart';
import '../services/api_client.dart';
import '../state/auth_state.dart';
import '../state/children_state.dart';
import '../theme/app_theme.dart';
import '../widgets/app_card.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';
import '../widgets/nurtura_app_bar.dart';

/// The privacy notice (#136).
///
/// With [consent], it is the screen a caregiver sees after signing in until
/// they agree to the current version: the notice, an "I agree" checkbox,
/// and log out. Without it, the notice opened from the Family tab to read.
class PrivacyNoticeScreen extends StatefulWidget {
  const PrivacyNoticeScreen({super.key, this.consent = false});

  final bool consent;

  @override
  State<PrivacyNoticeScreen> createState() => _PrivacyNoticeScreenState();
}

class _PrivacyNoticeScreenState extends State<PrivacyNoticeScreen> {
  PrivacyNotice? _notice;
  String? _loadError;
  bool _agreed = false;
  bool _saving = false;
  String? _saveError;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loadError = null);
    try {
      final notice = await context.read<AuthState>().privacyNotice();
      if (mounted) setState(() => _notice = notice);
    } on ApiException catch (e) {
      if (mounted) setState(() => _loadError = e.message);
    }
  }

  Future<void> _agree() async {
    final notice = _notice;
    if (notice == null || !_agreed || _saving) return;
    setState(() {
      _saving = true;
      _saveError = null;
    });
    try {
      // On success the app moves on to the home screen.
      await context.read<AuthState>().agreeToPrivacy(notice.version);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _saveError = e.message);
      // The wording changed since it was shown: show the new version.
      if (e.field('version') != null) {
        setState(() {
          _notice = null;
          _agreed = false;
          _saveError = e.field('version');
        });
        await _load();
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _logout() async {
    context.read<ChildrenState>().clear();
    await context.read<AuthState>().logout();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: widget.consent
          ? null
          : const NurturaAppBar(title: 'Privacy notice'),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: _body(),
          ),
        ),
      ),
    );
  }

  Widget _body() {
    final notice = _notice;
    if (notice == null && _loadError == null) {
      return const Center(child: CircularProgressIndicator());
    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 24, 20, 28),
      children: [
        if (widget.consent) ...[
          Text('Before you start', style: AppText.quicksand(size: 24)),
          const SizedBox(height: 6),
          Text(
            'Nurtura keeps some information about you and your child. '
            "Please read how it's used.",
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
        ],
        if (_saveError != null) ...[
          MessageBanner.error(_saveError!, key: const Key('privacyError')),
          const SizedBox(height: 12),
        ],
        if (notice == null) ...[
          MessageBanner.error(_loadError!, key: const Key('privacyLoadError')),
          const SizedBox(height: 12),
          SecondaryButton(
            key: const Key('privacyRetry'),
            label: 'Try again',
            icon: Icons.refresh_rounded,
            onPressed: _load,
          ),
        ] else
          AppCard(
            padding: const EdgeInsets.all(18),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(notice.title, style: AppText.quicksand(size: 19)),
                for (final section in notice.sections) ...[
                  const SizedBox(height: 14),
                  Text(
                    section.heading,
                    style: AppText.nunito(size: 14.5, weight: FontWeight.w800),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    section.body,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ],
            ),
          ),
        if (widget.consent) ...[
          const SizedBox(height: 16),
          CheckboxListTile(
            key: const Key('privacyAgreeCheckbox'),
            value: _agreed,
            onChanged: notice == null
                ? null
                : (v) => setState(() => _agreed = v ?? false),
            controlAffinity: ListTileControlAffinity.leading,
            contentPadding: EdgeInsets.zero,
            title: const Text(
              "I've read this. I'm the parent or guardian of the children I "
              'add, or have their permission.',
            ),
          ),
          const SizedBox(height: 12),
          PrimaryButton(
            key: const Key('privacyAgreeButton'),
            label: 'Agree and continue',
            icon: Icons.check_rounded,
            loading: _saving,
            onPressed: _agreed && notice != null ? _agree : null,
          ),
          const SizedBox(height: 8),
          Center(
            child: TextButton(
              key: const Key('privacyLogout'),
              onPressed: _saving ? null : _logout,
              child: const Text('Not now, log out'),
            ),
          ),
        ],
      ],
    );
  }
}
