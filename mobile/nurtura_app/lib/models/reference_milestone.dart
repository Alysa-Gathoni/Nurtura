/// A guideline milestone from the CDC/WHO catalogue.
class ReferenceMilestone {
  const ReferenceMilestone({
    required this.id,
    required this.key,
    required this.domain,
    required this.description,
    required this.expectedAgeMonths,
    required this.source,
  });

  factory ReferenceMilestone.fromJson(Map<String, dynamic> json) =>
      ReferenceMilestone(
        id: json['id'] as int,
        key: json['milestone_key'] as String,
        domain: json['domain'] as String,
        description: json['description'] as String,
        expectedAgeMonths: (json['expected_age_months'] as num).toDouble(),
        source: json['source'] as String,
      );

  final int id;
  final String key;
  final String domain;
  final String description;
  final double expectedAgeMonths;
  final String source;

  /// e.g. "By 12 months · CDC".
  String get expectedLabel {
    final age = expectedAgeMonths == expectedAgeMonths.roundToDouble()
        ? expectedAgeMonths.toInt().toString()
        : expectedAgeMonths.toString();
    return 'By $age months · $source';
  }
}

/// How the child is doing with a milestone (the rule engine's statuses).
enum MilestoneStatus {
  achieved('achieved', 'Achieved'),
  emerging('emerging', 'Emerging'),
  notYet('not_yet', 'Not yet');

  const MilestoneStatus(this.apiValue, this.label);

  final String apiValue;
  final String label;
}

/// A recorded observation and the regenerated profile's timestamp.
class RecordedMilestone {
  const RecordedMilestone({
    required this.description,
    required this.status,
    required this.profileGeneratedAt,
  });

  factory RecordedMilestone.fromJson(Map<String, dynamic> json) {
    final milestone = json['milestone'] as Map<String, dynamic>;
    final profile = json['profile'] as Map<String, dynamic>;
    return RecordedMilestone(
      description: milestone['description'] as String,
      status: MilestoneStatus.values.firstWhere(
        (s) => s.apiValue == milestone['status'],
      ),
      profileGeneratedAt: DateTime.parse(profile['generated_at'] as String),
    );
  }

  final String description;
  final MilestoneStatus status;
  final DateTime profileGeneratedAt;
}
