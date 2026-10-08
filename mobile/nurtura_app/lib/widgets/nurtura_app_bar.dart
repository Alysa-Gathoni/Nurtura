import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// Solid teal app bar with white bold title and rounded bottom corners.
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
      backgroundColor: AppColors.teal,
      foregroundColor: Colors.white,
      elevation: 0,
      scrolledUnderElevation: 0,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(bottom: Radius.circular(24)),
      ),
      title: Text(
        title,
        style: AppText.quicksand(size: 21, color: Colors.white),
      ),
      actions: actions,
    );
  }
}
