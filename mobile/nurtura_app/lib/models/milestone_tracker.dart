import 'reference_milestone.dart';

/// One milestone in the tracker (#192): what it is, when it is expected,
/// and its latest status, if any.
class TrackerMilestone {
  const TrackerMilestone({
    required this.id,
    required this.key,
    required this.description,
    required this.domain,
    required this.expectedAgeMonths,
    required this.source,
    required this.due,
    this.status,
    this.observedAtMonths,
  });

  factory TrackerMilestone.fromJson(Map<String, dynamic> json, String domain) =>
      TrackerMilestone(
        id: json['id'] as int,
        key: json['key'] as String,
        description: json['description'] as String,
        domain: domain,
        expectedAgeMonths: (json['expected_age_months'] as num).toDouble(),
        source: json['source'] as String? ?? '',
        due: json['due'] as bool? ?? false,
        status: _status(json['status'] as String?),
        observedAtMonths: json['observed_at_months'] as int?,
      );

  final int id;
  final String key;
  final String description;
  final String domain;
  final double expectedAgeMonths;
  final String source;

  /// The child is at or past the expected age.
  final bool due;

  /// Null when it hasn't been recorded.
  final MilestoneStatus? status;
  final int? observedAtMonths;

  String get expectedLabel => expectedAgeMonths % 1 == 0
      ? '${expectedAgeMonths.toInt()} months'
      : '$expectedAgeMonths months';

  /// For recording through [MilestoneService.record].
  ReferenceMilestone get reference => ReferenceMilestone(
    id: id,
    key: key,
    description: description,
    domain: domain,
    expectedAgeMonths: expectedAgeMonths,
    source: source,
  );
}

MilestoneStatus? _status(String? value) {
  for (final s in MilestoneStatus.values) {
    if (s.apiValue == value) return s;
  }
  return null;
}

/// The child's milestones by area (`GET /api/children/<id>/tracker/`).
class MilestoneTracker {
  const MilestoneTracker({
    required this.ageMonths,
    required this.prenatal,
    required this.areas,
  });

  factory MilestoneTracker.fromJson(Map<String, dynamic> json) =>
      MilestoneTracker(
        ageMonths: (json['age_months'] as num).toDouble(),
        prenatal: json['prenatal'] as bool? ?? false,
        areas: {
          for (final a in json['areas'] as List? ?? const [])
            (a as Map<String, dynamic>)['domain'] as String: [
              for (final m in a['milestones'] as List? ?? const [])
                TrackerMilestone.fromJson(
                  m as Map<String, dynamic>,
                  a['domain'] as String,
                ),
            ],
        },
      );

  final double ageMonths;
  final bool prenatal;

  /// Area (backend domain name) to its milestones, in the API's order.
  final Map<String, List<TrackerMilestone>> areas;
}

/// The weekly Nurtura observation (`GET /api/children/<id>/observation/`).
class NurturaObservation {
  const NurturaObservation({required this.text, this.focusDomain});

  factory NurturaObservation.fromJson(Map<String, dynamic> json) =>
      NurturaObservation(
        text: json['text'] as String? ?? '',
        focusDomain: json['focus_domain'] as String?,
      );

  final String text;
  final String? focusDomain;
}
