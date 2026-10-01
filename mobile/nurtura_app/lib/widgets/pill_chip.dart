import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// Fully rounded tag with bold text and a category colour.
///
/// Unselected chips use the soft [background] with [foreground] text and a
/// [color] icon; selected chips are filled with [color].
class PillChip extends StatelessWidget {
  const PillChip({
    super.key,
    required this.label,
    required this.color,
    required this.background,
    this.foreground = AppColors.ink,
    this.selectedForeground = Colors.white,
    this.selected = false,
    this.icon,
    this.trailingIcon,
    this.onTap,
  });

  final String label;
  final Color color;
  final Color background;
  final Color foreground;
  final Color selectedForeground;
  final bool selected;
  final IconData? icon;
  final IconData? trailingIcon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final textColor = selected ? selectedForeground : foreground;
    return Semantics(
      selected: onTap == null ? null : selected,
      button: onTap != null,
      child: Material(
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
                  Icon(icon, size: 15, color: selected ? textColor : color),
                  const SizedBox(width: 5),
                ],
                Text(
                  label,
                  style: AppText.nunito(
                    size: 12.5,
                    weight: FontWeight.w800,
                    color: textColor,
                  ),
                ),
                if (trailingIcon != null) ...[
                  const SizedBox(width: 4),
                  Icon(trailingIcon, size: 15, color: textColor),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
