import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// Inline message box for errors (coral) or information (gold).
class MessageBanner extends StatelessWidget {
  const MessageBanner.error(this.message, {super.key})
      : background = AppColors.coralSoft,
        iconColor = AppColors.coral,
        icon = Icons.error_outline_rounded;

  const MessageBanner.info(this.message, {super.key})
      : background = AppColors.goldSoft,
        iconColor = AppColors.ink,
        icon = Icons.info_outline_rounded;

  final String message;
  final Color background;
  final Color iconColor;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
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
              style: AppText.nunito(size: 14, weight: FontWeight.w700),
            ),
          ),
        ],
      ),
    );
  }
}
