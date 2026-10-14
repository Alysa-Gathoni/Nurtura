import 'package:flutter/material.dart';

import '../models/recommendation.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/domain_style.dart';
import '../utils/dates.dart';
import '../widgets/app_card.dart';
import '../widgets/nurtura_app_bar.dart';
import '../widgets/pill_chip.dart';
import 'recommendations_screen.dart';

/// One suggested activity in full, from the fields the recommendations API
/// already returns (no extra request, no scores).
class ActivityDetailScreen extends StatelessWidget {
  const ActivityDetailScreen({
    super.key,
    required this.recommendation,
    required this.childName,
  });

  final Recommendation recommendation;
  final String childName;

  @override
  Widget build(BuildContext context) {
    final r = recommendation;
    return Scaffold(
      appBar: const NurturaAppBar(title: 'Activity'),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: ListView(
              key: const Key('activityDetail'),
              padding: const EdgeInsets.all(20),
              children: [
                Text(r.activityName, style: AppText.quicksand(size: 24)),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    DomainChip(r.domain),
                    PillChip(
                      label: r.ageLabel,
                      color: context.palette.mutedText,
                      background: context.palette.card,
                      icon: Icons.child_care_rounded,
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                if (r.shortDescription.isNotEmpty)
                  AppCard(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'About this activity',
                          style: AppText.nunito(
                            size: 13,
                            weight: FontWeight.w800,
                            color: context.palette.mutedText,
                          ),
                        ),
                        const SizedBox(height: 6),
                        Text(
                          r.shortDescription,
                          style: AppText.nunito(size: 16, height: 1.4),
                        ),
                      ],
                    ),
                  ),
                if (r.hasExplanation) ...[
                  const SizedBox(height: 14),
                  ExplanationBox(r.explanation),
                ],
                const SizedBox(height: 16),
                Text(
                  'Suggested for $childName on ${formatDate(r.generatedAt.toLocal())}.',
                  key: const Key('suggestedOn'),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
