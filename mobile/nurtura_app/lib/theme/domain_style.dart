import 'package:flutter/material.dart';

import '../widgets/pill_chip.dart';
import 'app_colors.dart';

/// The five developmental domains, in the backend's spelling.
const developmentalDomains = [
  'Cognitive',
  'Language',
  'Motor',
  'Sensory',
  'Socio-Emotional',
];

/// Colour and icon for each developmental domain's tags.
class DomainStyle {
  const DomainStyle({
    required this.color,
    required this.background,
    required this.onColor,
    required this.icon,
  });

  final Color color;
  final Color background;
  final Color onColor;
  final IconData icon;

  static DomainStyle of(String domain) => switch (domain) {
    'Cognitive' => const DomainStyle(
      color: AppColors.gold,
      background: AppColors.goldSoft,
      onColor: AppColors.ink,
      icon: Icons.lightbulb_rounded,
    ),
    'Language' => const DomainStyle(
      color: AppColors.sky,
      background: AppColors.skySoft,
      onColor: Colors.white,
      icon: Icons.chat_bubble_rounded,
    ),
    'Motor' => const DomainStyle(
      color: AppColors.tealDeep,
      background: AppColors.mint,
      onColor: Colors.white,
      icon: Icons.directions_run_rounded,
    ),
    'Socio-Emotional' => const DomainStyle(
      color: AppColors.coral,
      background: AppColors.coralSoft,
      onColor: Colors.white,
      icon: Icons.favorite_rounded,
    ),
    // Sensory
    _ => DomainStyle(
      color: AppColors.teal,
      background: AppColors.tealLight.withValues(alpha: 0.3),
      onColor: Colors.white,
      icon: Icons.back_hand_rounded,
    ),
  };
}

/// A domain tag in its category colour.
class DomainChip extends StatelessWidget {
  const DomainChip(this.domain, {super.key, this.selected = false, this.onTap});

  final String domain;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final style = DomainStyle.of(domain);
    return PillChip(
      label: domain,
      icon: style.icon,
      color: style.color,
      background: style.background,
      selectedForeground: style.onColor,
      selected: selected,
      onTap: onTap,
    );
  }
}
