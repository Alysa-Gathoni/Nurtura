import 'package:flutter/material.dart';

import '../logic/password_strength.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// A three-part bar, a word and a checklist under a new-password field,
/// updated as the person types (#140). Hidden until they start.
class PasswordStrengthMeter extends StatelessWidget {
  const PasswordStrengthMeter({super.key, required this.password, this.email});

  final TextEditingController password;

  /// Checked against for "Not like your email", when known.
  final TextEditingController? email;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([password, ?email]),
      builder: (context, _) {
        final s = PasswordStrength.of(password.text, email: email?.text ?? '');
        return AnimatedSize(
          duration: const Duration(milliseconds: 200),
          alignment: Alignment.topCenter,
          child: s.isEmpty
              ? const SizedBox(width: double.infinity)
              : _meter(context, s),
        );
      },
    );
  }

  Widget _meter(BuildContext context, PasswordStrength s) {
    final p = context.palette;
    final color = switch (s.level) {
      0 => p.rose,
      1 => p.mustard,
      _ => p.sage,
    };
    return Padding(
      key: const Key('passwordStrength'),
      padding: const EdgeInsets.only(top: 10, left: 4, right: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              for (var i = 1; i <= 3; i++) ...[
                if (i > 1) const SizedBox(width: 6),
                Expanded(
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 220),
                    height: 6,
                    decoration: BoxDecoration(
                      color: i <= (s.level == 0 ? 1 : s.level)
                          ? color
                          : p.border,
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                ),
              ],
              const SizedBox(width: 12),
              Text(
                s.label,
                key: const Key('passwordStrengthLabel'),
                style: AppText.nunito(
                  size: 13,
                  weight: FontWeight.w800,
                  color: color,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 12,
            runSpacing: 4,
            children: [
              for (final rule in s.rules)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      rule.met
                          ? Icons.check_circle_rounded
                          : Icons.radio_button_unchecked_rounded,
                      size: 15,
                      color: rule.met ? p.sage : p.mutedText,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      rule.label,
                      style: AppText.nunito(
                        size: 12.5,
                        weight: FontWeight.w600,
                        color: rule.met ? p.ink : p.mutedText,
                      ),
                    ),
                  ],
                ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            s.tip,
            key: const Key('passwordStrengthTip'),
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}
