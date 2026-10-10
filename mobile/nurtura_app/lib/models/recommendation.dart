/// One recommended activity, as `/api/children/<id>/recommendations/` returns
/// it. The API sends no scores, so none can be shown.
class Recommendation {
  const Recommendation({
    required this.id,
    required this.batch,
    required this.position,
    required this.generatedAt,
    required this.activityId,
    required this.activityName,
    required this.domain,
    required this.ageRange,
    required this.shortDescription,
    required this.explanation,
  });

  factory Recommendation.fromJson(Map<String, dynamic> json) => Recommendation(
    id: json['id'] as int,
    batch: json['batch'] as String,
    position: json['position'] as int,
    generatedAt: DateTime.parse(json['generated_at'] as String),
    activityId: json['activity_id'] as String,
    activityName: json['activity_name'] as String,
    domain: json['developmental_domain'] as String,
    ageRange: json['age_range'] as String,
    shortDescription: json['short_description'] as String? ?? '',
    explanation: json['explanation'] as String? ?? '',
  );

  final int id;
  final String batch;

  /// Order within the batch; used for sorting only, never displayed.
  final int position;
  final DateTime generatedAt;
  final String activityId;
  final String activityName;
  final String domain;
  final String ageRange;
  final String shortDescription;
  final String explanation;

  bool get hasExplanation => explanation.trim().isNotEmpty;

  /// "Prenatal" as is; "6-12 months" with an en dash.
  String get ageLabel => ageRange.replaceAll('-', '–');

  Map<String, dynamic> toJson() => {
    'id': id,
    'batch': batch,
    'position': position,
    'generated_at': generatedAt.toIso8601String(),
    'activity_id': activityId,
    'activity_name': activityName,
    'developmental_domain': domain,
    'age_range': ageRange,
    'short_description': shortDescription,
    'explanation': explanation,
  };
}

/// The newest batch of recommendations for a child (possibly empty).
class RecommendationBatch {
  const RecommendationBatch({
    required this.batch,
    required this.generatedAt,
    required this.items,
  });

  factory RecommendationBatch.fromJson(Map<String, dynamic> json) {
    final items = [
      for (final r in json['recommendations'] as List? ?? const [])
        Recommendation.fromJson(r as Map<String, dynamic>),
    ]..sort((a, b) => a.position.compareTo(b.position));
    final generated = json['generated_at'] as String?;
    return RecommendationBatch(
      batch: json['batch'] as String?,
      generatedAt: generated == null ? null : DateTime.parse(generated),
      items: items,
    );
  }

  final String? batch;
  final DateTime? generatedAt;
  final List<Recommendation> items;

  bool get isEmpty => items.isEmpty;

  Map<String, dynamic> toJson() => {
    'batch': batch,
    'generated_at': generatedAt?.toIso8601String(),
    'recommendations': [for (final r in items) r.toJson()],
  };
}
