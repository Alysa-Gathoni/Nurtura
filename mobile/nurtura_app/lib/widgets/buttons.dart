import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// Solid teal button with a soft coloured shadow.
///
/// While [loading] it shows a spinner and ignores taps, so a request can't be
/// sent twice.
class PrimaryButton extends StatelessWidget {
  const PrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.loading = false,
    this.icon,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool loading;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final enabled = onPressed != null && !loading;
    return _ButtonShell(
      background: enabled
          ? context.palette.primary
          : context.palette.primary.withValues(alpha: 0.55),
      shadow: enabled ? AppShadows.primaryButton : const [],
      onTap: enabled ? onPressed : null,
      child: loading
          ? SizedBox(
              key: const Key('buttonSpinner'),
              width: 22,
              height: 22,
              child: CircularProgressIndicator(
                strokeWidth: 2.6,
                color: context.palette.onPrimary,
              ),
            )
          : _ButtonLabel(
              label: label,
              icon: icon,
              color: context.palette.onPrimary,
            ),
    );
  }
}

/// Mint button with teal text and no shadow.
class SecondaryButton extends StatelessWidget {
  const SecondaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return _ButtonShell(
      background: context.palette.primarySoft,
      shadow: const [],
      onTap: onPressed,
      child: _ButtonLabel(
        label: label,
        icon: icon,
        color: context.palette.primary,
      ),
    );
  }
}

class _ButtonShell extends StatelessWidget {
  const _ButtonShell({
    required this.background,
    required this.shadow,
    required this.onTap,
    required this.child,
  });

  final Color background;
  final List<BoxShadow> shadow;
  final VoidCallback? onTap;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final radius = BorderRadius.circular(AppRadii.button);
    return Container(
      decoration: BoxDecoration(
        color: background,
        borderRadius: radius,
        boxShadow: shadow,
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: radius,
        child: InkWell(
          borderRadius: radius,
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 52),
            child: Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: child,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ButtonLabel extends StatelessWidget {
  const _ButtonLabel({required this.label, required this.color, this.icon});

  final String label;
  final Color color;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    // Long labels shrink with an ellipsis rather than overflowing.
    final text = Text(
      label,
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
      style: AppText.nunito(size: 16, weight: FontWeight.w800, color: color),
    );
    if (icon == null) return text;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: color, size: 20),
        const SizedBox(width: 8),
        Flexible(child: text),
      ],
    );
  }
}
