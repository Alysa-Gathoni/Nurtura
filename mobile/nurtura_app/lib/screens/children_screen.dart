import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/child_profile.dart';
import '../services/api_client.dart';
import '../state/auth_state.dart';
import '../state/children_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/domain_style.dart';
import '../widgets/app_card.dart';
import '../widgets/app_text_field.dart';
import '../widgets/buttons.dart';
import '../widgets/fingerprint_lock_tile.dart';
import '../widgets/gamification.dart';
import '../widgets/message_banner.dart';
import '../widgets/nurtura_app_bar.dart';
import '../widgets/pill_chip.dart';
import '../widgets/theme_picker.dart';
import '../widgets/village.dart';
import 'change_password_screen.dart';
import 'child_form_screen.dart';
import 'milestone_screen.dart';
import 'privacy_notice_screen.dart';

/// The caregiver's children and app settings.
///
/// Standalone (before there is a child) it is a full screen with loading,
/// errors and "Add your first child". In the home shell ([embedded]) it is
/// the Family tab: the children (each can be edited or deleted), light/dark
/// mode, logging out and deleting the account (#134).
class ChildrenScreen extends StatefulWidget {
  const ChildrenScreen({
    super.key,
    this.embedded = false,
    this.onOpenChild,
    this.onChildAdded,
  });

  final bool embedded;

  /// Tapping a child; by default opens their milestones.
  final ValueChanged<ChildProfile>? onOpenChild;

  /// A child was added; by default opens their milestones.
  final ValueChanged<ChildProfile>? onChildAdded;

  @override
  State<ChildrenScreen> createState() => _ChildrenScreenState();
}

class _ChildrenScreenState extends State<ChildrenScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final children = context.read<ChildrenState>();
      if (!children.loaded && !children.loading) children.load();
    });
  }

  Future<void> _addChild() async {
    final child = await Navigator.of(context).push<ChildProfile>(
      MaterialPageRoute(builder: (_) => const ChildFormScreen()),
    );
    if (child == null || !mounted) return;
    if (widget.onChildAdded != null) return widget.onChildAdded!(child);
    _openMilestones(child, justCreated: true);
  }

  Future<void> _editChild(ChildProfile child) async {
    await Navigator.of(context).push<ChildProfile>(
      MaterialPageRoute(builder: (_) => ChildFormScreen(child: child)),
    );
    if (!mounted) return;
    final kept = context.read<ChildrenState>().children.any(
      (c) => c.id == child.id,
    );
    if (!kept) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("${child.name}'s profile was deleted.")),
      );
    }
  }

  void _openChild(ChildProfile child) {
    if (widget.onOpenChild != null) return widget.onOpenChild!(child);
    _openMilestones(child);
  }

  void _openMilestones(ChildProfile child, {bool justCreated = false}) {
    // The milestone screen confirms a new profile itself: a SnackBar here
    // would float over the "Add a child" button when the caregiver comes back.
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => MilestoneScreen(child: child, justCreated: justCreated),
      ),
    );
  }

  Future<void> _logout() async {
    context.read<ChildrenState>().clear();
    await context.read<AuthState>().logout();
  }

  Future<void> _deleteAccount() async {
    final children = context.read<ChildrenState>();
    final deleted = await showDialog<bool>(
      context: context,
      builder: (_) => const _DeleteAccountDialog(),
    );
    if (deleted == true) children.clear();
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<ChildrenState>();
    final body = Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 560),
        child: _body(state),
      ),
    );
    if (widget.embedded) return body;
    return Scaffold(
      appBar: NurturaAppBar(
        title: 'Your children',
        actions: [
          IconButton(
            key: const Key('logoutButton'),
            tooltip: 'Log out',
            icon: const Icon(Icons.logout_rounded),
            onPressed: _logout,
          ),
          PopupMenuButton<VoidCallback>(
            key: const Key('accountMenu'),
            tooltip: 'Account',
            onSelected: (action) => action(),
            itemBuilder: (_) => [
              PopupMenuItem(
                key: const Key('deleteAccountButton'),
                value: _deleteAccount,
                child: const Text('Delete account'),
              ),
            ],
          ),
        ],
      ),
      body: SafeArea(child: body),
    );
  }

  Widget _body(ChildrenState state) {
    if (!state.loaded && state.error == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (!state.loaded) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            MessageBanner.error(state.error!.message),
            const SizedBox(height: 14),
            SecondaryButton(
              key: const Key('retryButton'),
              label: 'Try again',
              icon: Icons.refresh_rounded,
              onPressed: state.loading ? null : state.load,
            ),
          ],
        ),
      );
    }
    if (state.children.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: AppCard(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Padding(
                  padding: EdgeInsets.only(bottom: 14),
                  child: Center(child: VillageMark(size: 88)),
                ),
                Text(
                  'Add your first child',
                  textAlign: TextAlign.center,
                  style: AppText.quicksand(size: 22),
                ),
                const SizedBox(height: 6),
                Text(
                  'Tell us about your little one, or the baby on the way.',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 18),
                PrimaryButton(
                  key: const Key('addChildButton'),
                  label: 'Add a child',
                  icon: Icons.add_rounded,
                  onPressed: _addChild,
                ),
              ],
            ),
          ),
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: state.load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        children: [
          if (state.offline) ...[
            const MessageBanner.info(
              "You're offline. This is the list saved on your phone.",
              key: Key('offlineChildrenNotice'),
            ),
            const SizedBox(height: 12),
          ],
          if (widget.embedded)
            Text('Your children', style: AppText.quicksand(size: 20)),
          if (widget.embedded) const SizedBox(height: 10),
          for (final child in state.children) ...[
            _ChildCard(
              child: child,
              selected: widget.embedded && child.id == state.selected?.id,
              onTap: () => _openChild(child),
              onEdit: () => _editChild(child),
            ),
            const SizedBox(height: 12),
          ],
          PrimaryButton(
            key: const Key('addChildButton'),
            label: 'Add a child',
            icon: Icons.add_rounded,
            onPressed: _addChild,
          ),
          if (widget.embedded) ...[
            const SizedBox(height: 26),
            Text('Account', style: AppText.quicksand(size: 20)),
            const SizedBox(height: 10),
            const _AccountCard(),
            const SizedBox(height: 26),
            Text('Appearance', style: AppText.quicksand(size: 20)),
            const SizedBox(height: 10),
            const ThemePicker(),
            const SizedBox(height: 14),
            Center(
              child: TextButton.icon(
                key: const Key('privacyNoticeButton'),
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => const PrivacyNoticeScreen(),
                  ),
                ),
                icon: const Icon(Icons.privacy_tip_outlined),
                label: const Text('Privacy notice'),
              ),
            ),
            const SizedBox(height: 12),
            SecondaryButton(
              key: const Key('logoutButton'),
              label: 'Log out',
              icon: Icons.logout_rounded,
              onPressed: _logout,
            ),
            const SizedBox(height: 10),
            Center(
              child: TextButton.icon(
                key: const Key('deleteAccountButton'),
                style: TextButton.styleFrom(
                  foregroundColor: context.palette.rose,
                ),
                onPressed: _deleteAccount,
                icon: const Icon(Icons.delete_outline_rounded),
                label: const Text('Delete account'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ChildCard extends StatelessWidget {
  const _ChildCard({
    required this.child,
    required this.onTap,
    required this.onEdit,
    this.selected = false,
  });

  final ChildProfile child;
  final VoidCallback onTap;
  final VoidCallback onEdit;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return AppCard(
      key: Key('child_${child.id}'),
      onTap: onTap,
      borderColor: selected ? p.primaryMid : null,
      child: Row(
        children: [
          ChildAvatar(child: child, size: 52),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        child.name,
                        overflow: TextOverflow.ellipsis,
                        style: AppText.quicksand(size: 19),
                      ),
                    ),
                    if (child.isExpecting) ...[
                      const SizedBox(width: 8),
                      PillChip(
                        label: 'Expecting',
                        color: p.mustard,
                        background: p.mustardSoft,
                        icon: Icons.favorite_rounded,
                      ),
                    ],
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  child.ageDescription,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                if (child.concerns.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [for (final d in child.concerns) DomainChip(d)],
                  ),
                ],
              ],
            ),
          ),
          IconButton(
            key: Key('editChild_${child.id}'),
            tooltip: 'Edit ${child.name}',
            icon: Icon(Icons.edit_rounded, color: p.mutedText),
            onPressed: onEdit,
          ),
        ],
      ),
    );
  }
}

/// Confirms deleting the account with the password (#134).
///
/// An account with no password (for example one made with Google) is
/// confirmed with its email instead: the server says which, and the field
/// switches. Pops true once the account is deleted and the session ended.
class _DeleteAccountDialog extends StatefulWidget {
  const _DeleteAccountDialog();

  @override
  State<_DeleteAccountDialog> createState() => _DeleteAccountDialogState();
}

class _DeleteAccountDialogState extends State<_DeleteAccountDialog> {
  final _field = TextEditingController();
  bool _byEmail = false;
  bool _deleting = false;
  String? _error;

  @override
  void dispose() {
    _field.dispose();
    super.dispose();
  }

  Future<void> _confirm() async {
    if (_deleting) return;
    final value = _field.text;
    if (value.trim().isEmpty) {
      return setState(
        () => _error = _byEmail ? 'Type your email.' : 'Type your password.',
      );
    }
    setState(() {
      _deleting = true;
      _error = null;
    });
    final navigator = Navigator.of(context);
    try {
      await context.read<AuthState>().deleteAccount(
        password: _byEmail ? null : value,
        email: _byEmail ? value.trim() : null,
      );
      navigator.pop(true);
    } on ApiException catch (e) {
      if (!mounted) return;
      final emailError = e.field('email');
      setState(() {
        _deleting = false;
        if (emailError != null && !_byEmail) {
          // No password on this account: ask for its email instead.
          _byEmail = true;
          _field.clear();
          _error = null;
        } else {
          _error = e.field(_byEmail ? 'email' : 'password') ?? e.message;
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Delete your account?'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              "This deletes your account and everything in it: your children's "
              "profiles, milestones, ideas and ratings. This can't be undone.",
            ),
            const SizedBox(height: 16),
            if (_byEmail) ...[
              const Text(
                "Your account doesn't have a password, so type its email "
                'address to confirm.',
              ),
              const SizedBox(height: 10),
            ],
            AppTextField(
              key: const Key('deleteAccountField'),
              label: _byEmail ? 'Your email' : 'Your password',
              controller: _field,
              obscureText: !_byEmail,
              keyboardType: _byEmail ? TextInputType.emailAddress : null,
              prefixIcon: _byEmail ? Icons.mail_rounded : Icons.lock_rounded,
              errorText: _error,
              onSubmitted: (_) => _confirm(),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _deleting ? null : () => Navigator.pop(context, false),
          child: const Text('Cancel'),
        ),
        TextButton(
          key: const Key('confirmDeleteAccount'),
          style: TextButton.styleFrom(foregroundColor: context.palette.rose),
          onPressed: _deleting ? null : _confirm,
          child: _deleting
              ? const SizedBox(
                  width: 18,
                  height: 18,
                  child: CircularProgressIndicator(strokeWidth: 2.2),
                )
              : const Text('Delete account'),
        ),
      ],
    );
  }
}

/// Who is signed in, so a shared phone shows whose family this is (#138).
class _AccountCard extends StatelessWidget {
  const _AccountCard();

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final email = context.watch<AuthState>().user?.email;
    return AppCard(
      key: const Key('accountCard'),
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              CircleAvatar(
                radius: 22,
                backgroundColor: p.primarySoft,
                child: Icon(Icons.person_rounded, color: p.primary),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      email ?? 'Signed in',
                      key: const Key('accountEmail'),
                      overflow: TextOverflow.ellipsis,
                      style: AppText.nunito(size: 15, weight: FontWeight.w800),
                    ),
                    Text(
                      'Caregiver',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Divider(color: p.border, height: 1),
          TextButton.icon(
            key: const Key('passwordSettingsButton'),
            onPressed: () => openPasswordSettings(context),
            icon: const Icon(Icons.lock_reset_rounded),
            label: Text(passwordSettingsLabel(context)),
          ),
          const FingerprintLockTile(),
        ],
      ),
    );
  }
}
