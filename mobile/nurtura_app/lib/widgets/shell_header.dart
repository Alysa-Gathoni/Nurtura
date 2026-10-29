import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/child_profile.dart';
import '../state/children_state.dart';
import '../state/engagement.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import 'buttons.dart';
import 'gamification.dart';
import 'village.dart';

/// The header of each tab, on a watercolour wash: the selected child (tap to
/// switch), the day streak, and the tab's title.
class ShellHeader extends StatelessWidget {
  const ShellHeader({
    super.key,
    required this.title,
    this.subtitle,
    this.showChild = true,
    this.onAddChild,
    this.trailing,
  });

  final String title;
  final String? subtitle;
  final bool showChild;
  final VoidCallback? onAddChild;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final child = context.watch<ChildrenState>().selected;
    final streak = context.watch<EngagementState>().streak;
    return VillageWash(
      seed: title.length,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  if (showChild && child != null)
                    Expanded(
                      child: _ChildSwitcherButton(
                        child: child,
                        onAddChild: onAddChild,
                      ),
                    )
                  else
                    const Spacer(),
                  ?trailing,
                  const SizedBox(width: 8),
                  StreakChip(days: streak),
                ],
              ),
              const SizedBox(height: 16),
              Text(title, style: AppText.quicksand(size: 28, color: p.ink)),
              if (subtitle != null) ...[
                const SizedBox(height: 2),
                Text(
                  subtitle!,
                  style: AppText.nunito(
                    size: 14.5,
                    weight: FontWeight.w600,
                    color: p.mutedText,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _ChildSwitcherButton extends StatelessWidget {
  const _ChildSwitcherButton({required this.child, this.onAddChild});

  final ChildProfile child;
  final VoidCallback? onAddChild;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Align(
      alignment: Alignment.centerLeft,
      child: Material(
        color: p.card,
        shape: StadiumBorder(side: BorderSide(color: p.border)),
        child: InkWell(
          key: const Key('childSwitcher'),
          customBorder: const StadiumBorder(),
          onTap: () => showChildSwitcher(context, onAddChild: onAddChild),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(4, 4, 12, 4),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                ChildAvatar(child: child, size: 36),
                const SizedBox(width: 8),
                Flexible(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        child.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: AppText.nunito(
                          size: 15,
                          weight: FontWeight.w800,
                          color: p.ink,
                        ),
                      ),
                      Text(
                        child.ageDescription,
                        maxLines: 1,
                        style: AppText.nunito(
                          size: 12,
                          weight: FontWeight.w600,
                          color: p.mutedText,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 4),
                Icon(Icons.expand_more_rounded, color: p.mutedText, size: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Bottom sheet listing the children to switch between.
Future<void> showChildSwitcher(
  BuildContext context, {
  VoidCallback? onAddChild,
}) {
  return showModalBottomSheet(
    context: context,
    builder: (sheetContext) {
      final state = context.read<ChildrenState>();
      final p = sheetContext.palette;
      return SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Switch child', style: AppText.quicksand(size: 20)),
              const SizedBox(height: 12),
              for (final c in state.children)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Material(
                    color: c.id == state.selected?.id
                        ? p.primarySoft
                        : p.cardAlt,
                    borderRadius: BorderRadius.circular(AppRadii.card),
                    child: ListTile(
                      key: Key('switch_${c.id}'),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppRadii.card),
                      ),
                      leading: ChildAvatar(child: c, size: 40),
                      title: Text(
                        c.name,
                        style: AppText.nunito(
                          size: 16,
                          weight: FontWeight.w800,
                        ),
                      ),
                      subtitle: Text(
                        c.ageDescription,
                        style: Theme.of(sheetContext).textTheme.bodySmall,
                      ),
                      trailing: c.id == state.selected?.id
                          ? Icon(Icons.check_circle_rounded, color: p.primary)
                          : null,
                      onTap: () {
                        state.select(c);
                        Navigator.of(sheetContext).pop();
                      },
                    ),
                  ),
                ),
              if (onAddChild != null) ...[
                const SizedBox(height: 4),
                SecondaryButton(
                  label: 'Add a child',
                  icon: Icons.add_rounded,
                  onPressed: () {
                    Navigator.of(sheetContext).pop();
                    onAddChild();
                  },
                ),
              ],
            ],
          ),
        ),
      );
    },
  );
}
