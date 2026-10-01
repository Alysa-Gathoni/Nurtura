import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Fully rounded tag with bold text and a category colour.
///
/// Unselected chips use the soft [background] with [color] text; selected
/// chips are filled with [color] and white text.
class PillChip extends StatelessWidget {
  const PillChip({
    super.key,
    required this.label,
    required this.color,
    required this.background,
    this.selected = false,
    this.icon,
    this.onTap,
  });

  final String label;
  final Color color;
  final Color background;
  final bool selected;
  final IconData? icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final foreground = selected ? Colors.white : color;
    return Material(
      color: selected ? color : background,
      shape: const StadiumBorder(),
      child: InkWell(
        customBorder: const StadiumBorder(),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (icon != null) ...[
                Icon(icon, size: 15, color: foreground),
                const SizedBox(width: 5),
              ],
              Text(
                label,
                style: AppText.nunito(
                  size: 12.5,
                  weight: FontWeight.w800,
                  color: foreground,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
