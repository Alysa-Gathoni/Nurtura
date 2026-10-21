import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/child_profile.dart';
import '../state/auth_state.dart';
import '../state/children_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/domain_style.dart';
import '../widgets/app_card.dart';
import '../widgets/buttons.dart';
import '../widgets/gamification.dart';
import '../widgets/message_banner.dart';
import '../widgets/nurtura_app_bar.dart';
import '../widgets/pill_chip.dart';
import '../widgets/theme_picker.dart';
import '../widgets/village.dart';
import 'child_form_screen.dart';
import 'milestone_screen.dart';

/// The caregiver's children and app settings.
///
/// Standalone (before there is a child) it is a full screen with loading,
/// errors and "Add your first child". In the home shell ([embedded]) it is
/// the Family tab: the children, light/dark mode and logging out.
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
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
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
            Text('Appearance', style: AppText.quicksand(size: 20)),
            const SizedBox(height: 10),
            const ThemePicker(),
            const SizedBox(height: 26),
            SecondaryButton(
              key: const Key('logoutButton'),
              label: 'Log out',
              icon: Icons.logout_rounded,
              onPressed: _logout,
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
    this.selected = false,
  });

  final ChildProfile child;
  final VoidCallback onTap;
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
          Icon(Icons.chevron_right_rounded, color: p.mutedText),
        ],
      ),
    );
  }
}
