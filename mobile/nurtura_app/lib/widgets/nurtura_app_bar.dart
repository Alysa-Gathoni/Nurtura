import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// A quiet linen app bar with the title in the heading font.
class NurturaAppBar extends StatelessWidget implements PreferredSizeWidget {
  const NurturaAppBar({super.key, required this.title, this.actions});

  final String title;
  final List<Widget>? actions;

  @override
  Size get preferredSize => const Size.fromHeight(64);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      toolbarHeight: 64,
      backgroundColor: context.palette.paper,
      foregroundColor: context.palette.ink,
      surfaceTintColor: Colors.transparent,
      elevation: 0,
      scrolledUnderElevation: 0,
      shape: Border(bottom: BorderSide(color: context.palette.border)),
      title: Text(
        title,
        style: AppText.quicksand(size: 21, color: context.palette.ink),
      ),
      actions: actions,
    );
  }
}
