import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// A paper card on the linen background: a hairline edge and, in light
/// mode, a faint warm lift.
class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(14),
    this.color,
    this.borderColor,
    this.onTap,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  /// Defaults to the theme's card colour.
  final Color? color;
  final Color? borderColor;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final dark = Theme.of(context).brightness == Brightness.dark;
    final radius = BorderRadius.circular(AppRadii.card);
    return Container(
      decoration: BoxDecoration(
        color: color ?? p.card,
        borderRadius: radius,
        boxShadow: dark ? null : AppShadows.card,
        border: borderColor != null
            ? Border.all(color: borderColor!, width: 2)
            : Border.all(color: p.border),
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: radius,
        child: InkWell(
          borderRadius: radius,
          onTap: onTap,
          child: Padding(padding: padding, child: child),
        ),
      ),
    );
  }
}
