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

/// Plain words for each domain, for tiles and headings.
const domainLabels = {
  'Cognitive': 'Thinking',
  'Language': 'Talking',
  'Motor': 'Moving',
  'Sensory': 'Senses',
  'Socio-Emotional': 'Feelings',
};

/// Colour and icon for each developmental domain.
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

  static DomainStyle of(String domain, NurturaPalette p) => switch (domain) {
    'Cognitive' => DomainStyle(
      color: p.mustard,
      background: p.mustardSoft,
      onColor: p.ink == AppColors.ink ? AppColors.ink : p.onPrimary,
      icon: Icons.lightbulb_rounded,
    ),
    'Language' => DomainStyle(
      color: p.dusk,
      background: p.duskSoft,
      onColor: p.onPrimary,
      icon: Icons.chat_bubble_rounded,
    ),
    'Motor' => DomainStyle(
      color: p.sage,
      background: p.sageSoft,
      onColor: p.onPrimary,
      icon: Icons.directions_run_rounded,
    ),
    'Socio-Emotional' => DomainStyle(
      color: p.rose,
      background: p.roseSoft,
      onColor: p.onPrimary,
      icon: Icons.favorite_rounded,
    ),
    // Sensory
    _ => DomainStyle(
      color: p.plum,
      background: p.plumSoft,
      onColor: p.onPrimary,
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
    final style = DomainStyle.of(domain, context.palette);
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
