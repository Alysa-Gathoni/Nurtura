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
import '../widgets/message_banner.dart';
import '../widgets/nurtura_app_bar.dart';
import '../widgets/pill_chip.dart';
import 'child_form_screen.dart';

/// The caregiver's children; the signed-in home screen.
class ChildrenScreen extends StatefulWidget {
  const ChildrenScreen({super.key});

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
    if (child != null && mounted) _openChild(child, justCreated: true);
  }

  void _openChild(ChildProfile child, {bool justCreated = false}) {
    // Milestone recording for the child is added in #25.
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          justCreated
              ? "${child.name}'s profile is saved."
              : 'Milestone recording for ${child.name} is coming next.',
        ),
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
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: _body(state),
          ),
        ),
      ),
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
            padding: const EdgeInsets.all(22),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(
                  Icons.family_restroom_rounded,
                  size: 48,
                  color: AppColors.teal,
                ),
                const SizedBox(height: 10),
                Text(
                  'Add your first child',
                  textAlign: TextAlign.center,
                  style: AppText.quicksand(size: 22),
                ),
                const SizedBox(height: 6),
                Text(
                  "Tell us about your child, or the baby you're expecting, "
                  'to start tracking milestones.',
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
    return Column(
      children: [
        Expanded(
          child: RefreshIndicator(
            onRefresh: state.load,
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 8),
              itemCount: state.children.length,
              separatorBuilder: (_, _) => const SizedBox(height: 12),
              itemBuilder: (_, i) => _ChildCard(
                child: state.children[i],
                onTap: () => _openChild(state.children[i]),
              ),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
          child: PrimaryButton(
            key: const Key('addChildButton'),
            label: 'Add a child',
            icon: Icons.add_rounded,
            onPressed: _addChild,
          ),
        ),
      ],
    );
  }
}

class _ChildCard extends StatelessWidget {
  const _ChildCard({required this.child, required this.onTap});

  final ChildProfile child;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      key: Key('child_${child.id}'),
      onTap: onTap,
      child: Row(
        children: [
          Container(
            width: 52,
            height: 52,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                colors: child.isExpecting
                    ? const [AppColors.coral, AppColors.gold]
                    : const [AppColors.teal, AppColors.tealLight],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
            child: Text(
              child.name.isEmpty ? '?' : child.name[0].toUpperCase(),
              style: AppText.quicksand(size: 22, color: Colors.white),
            ),
          ),
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
                      const PillChip(
                        label: 'Expecting',
                        color: AppColors.gold,
                        background: AppColors.goldSoft,
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
          const Icon(Icons.chevron_right_rounded, color: AppColors.mutedText),
        ],
      ),
    );
  }
}
