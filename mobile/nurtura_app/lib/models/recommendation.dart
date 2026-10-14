/// The caregiver marked the activity as done, fully or partly (FR-14).
class Completion {
  const Completion({required this.partial, required this.date});

  factory Completion.fromJson(Map<String, dynamic> json) => Completion(
    partial: json['status'] == 'partially_completed',
    date: DateTime.parse(json['completion_date'] as String),
  );

  final bool partial;
  final DateTime date;

  String get label => partial ? 'Partly done' : 'Done';

  Map<String, dynamic> toJson() => {
    'status': partial ? 'partially_completed' : 'completed',
    'completion_date':
        '${date.year.toString().padLeft(4, '0')}-'
        '${date.month.toString().padLeft(2, '0')}-'
        '${date.day.toString().padLeft(2, '0')}',
  };
}

/// The caregiver's rating and comment on a recommendation (FR-15).
class ActivityFeedback {
  const ActivityFeedback({
    required this.rating,
    required this.comment,
    required this.submittedAt,
  });

  factory ActivityFeedback.fromJson(Map<String, dynamic> json) =>
      ActivityFeedback(
        rating: json['rating'] as int,
        comment: json['comment'] as String? ?? '',
        submittedAt: DateTime.parse(json['date_submitted'] as String),
      );

  final int rating;
  final String comment;
  final DateTime submittedAt;

  Map<String, dynamic> toJson() => {
    'rating': rating,
    'comment': comment,
    'date_submitted': submittedAt.toIso8601String(),
  };
}

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
    this.completion,
    this.feedback,
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
    completion: json['completion'] == null
        ? null
        : Completion.fromJson(json['completion'] as Map<String, dynamic>),
    feedback: json['feedback'] == null
        ? null
        : ActivityFeedback.fromJson(json['feedback'] as Map<String, dynamic>),
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
  final Completion? completion;
  final ActivityFeedback? feedback;

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
    'completion': completion?.toJson(),
    'feedback': feedback?.toJson(),
  };

  /// A copy with a new completion (null clears it) and/or feedback.
  Recommendation withProgress({
    Completion? Function()? completion,
    ActivityFeedback? feedback,
  }) => Recommendation(
    id: id,
    batch: batch,
    position: position,
    generatedAt: generatedAt,
    activityId: activityId,
    activityName: activityName,
    domain: domain,
    ageRange: ageRange,
    shortDescription: shortDescription,
    explanation: explanation,
    completion: completion == null ? this.completion : completion(),
    feedback: feedback ?? this.feedback,
  );
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

  /// The same batch with [updated] in place of the item with its id.
  RecommendationBatch replacing(Recommendation updated) => RecommendationBatch(
    batch: batch,
    generatedAt: generatedAt,
    items: [for (final r in items) r.id == updated.id ? updated : r],
  );

  Map<String, dynamic> toJson() => {
    'batch': batch,
    'generated_at': generatedAt?.toIso8601String(),
    'recommendations': [for (final r in items) r.toJson()],
  };
}
