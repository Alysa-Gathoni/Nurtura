import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

enum _Kind { error, success, info }

/// Inline message box for errors (rose), success (sage) or information (mustard).
class MessageBanner extends StatelessWidget {
  const MessageBanner.error(this.message, {super.key}) : _kind = _Kind.error;

  const MessageBanner.success(this.message, {super.key})
    : _kind = _Kind.success;

  const MessageBanner.info(this.message, {super.key}) : _kind = _Kind.info;

  final String message;
  final _Kind _kind;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final (background, iconColor, icon) = switch (_kind) {
      _Kind.error => (p.roseSoft, p.rose, Icons.error_outline_rounded),
      _Kind.success => (p.sageSoft, p.sage, Icons.check_circle_rounded),
      _Kind.info => (p.mustardSoft, p.mustard, Icons.info_outline_rounded),
    };
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppRadii.field),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: iconColor, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: AppText.nunito(
                size: 14,
                weight: FontWeight.w700,
                color: p.ink,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
