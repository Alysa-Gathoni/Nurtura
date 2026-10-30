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
    this.description = '',
    this.materials = '',
    this.culturalRelevance = '',
    this.source = '',
    this.sourceUrl = '',
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
    description: json['description'] as String? ?? '',
    materials: json['materials'] as String? ?? '',
    culturalRelevance: json['cultural_relevance'] as String? ?? '',
    source: json['source'] as String? ?? '',
    sourceUrl: json['source_url'] as String? ?? '',
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

  /// The full activity (#138). Empty in ideas saved on the phone before the
  /// API sent them, so the screen falls back to [shortDescription].
  final String description;
  final String materials;
  final String culturalRelevance;
  final String source;
  final String sourceUrl;
  final String explanation;
  final Completion? completion;
  final ActivityFeedback? feedback;

  bool get hasExplanation => explanation.trim().isNotEmpty;

  /// "Prenatal" as is; "6-12 months" with an en dash.
  String get ageLabel => ageRange.replaceAll('-', '–');

  /// The full steps when known, otherwise the shortened ones.
  String get howToPlay =>
      description.trim().isNotEmpty ? description.trim() : shortDescription;

  /// The source link's site ("cdc.gov"), or null without a link. The whole
  /// link is too long to read on a phone.
  String? get sourceSite {
    final host = Uri.tryParse(sourceUrl.trim())?.host ?? '';
    return host.isEmpty ? null : host.replaceFirst(RegExp(r'^www\.'), '');
  }

  /// What's needed, or null when nothing is ("None") or it isn't known.
  String? get materialsNeeded {
    final m = materials.trim();
    if (m.isEmpty || m.toLowerCase().replaceAll('.', '') == 'none') return null;
    return m;
  }

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
    'description': description,
    'materials': materials,
    'cultural_relevance': culturalRelevance,
    'source': source,
    'source_url': sourceUrl,
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
    description: description,
    materials: materials,
    culturalRelevance: culturalRelevance,
    source: source,
    sourceUrl: sourceUrl,
    explanation: explanation,
    completion: completion == null ? this.completion : completion(),
    feedback: feedback ?? this.feedback,
  );
}

/// A gentle suggestion to mention due "Not yet" milestones at the next
/// clinic visit (#161). Never a diagnosis, and never part of the ranking.
class Referral {
  const Referral({required this.message, required this.milestones});

  factory Referral.fromJson(Map<String, dynamic> json) => Referral(
    message: json['message'] as String,
    milestones: [
      for (final m in json['milestones'] as List? ?? const [])
        (m as Map<String, dynamic>)['description'] as String,
    ],
  );

  final String message;

  /// Descriptions of the due milestones marked "Not yet".
  final List<String> milestones;

  Map<String, dynamic> toJson() => {
    'message': message,
    'milestones': [
      for (final m in milestones) {'description': m},
    ],
  };
}

/// The newest batch of recommendations for a child (possibly empty).
class RecommendationBatch {
  const RecommendationBatch({
    required this.batch,
    required this.generatedAt,
    required this.items,
    this.referral,
  });

  factory RecommendationBatch.fromJson(Map<String, dynamic> json) {
    final items = [
      for (final r in json['recommendations'] as List? ?? const [])
        Recommendation.fromJson(r as Map<String, dynamic>),
    ]..sort((a, b) => a.position.compareTo(b.position));
    final generated = json['generated_at'] as String?;
    final referral = json['referral'] as Map<String, dynamic>?;
    return RecommendationBatch(
      batch: json['batch'] as String?,
      generatedAt: generated == null ? null : DateTime.parse(generated),
      items: items,
      referral: referral == null ? null : Referral.fromJson(referral),
    );
  }

  final String? batch;
  final DateTime? generatedAt;
  final List<Recommendation> items;
  final Referral? referral;

  bool get isEmpty => items.isEmpty;

  /// The same batch with [updated] in place of the item with its id.
  RecommendationBatch replacing(Recommendation updated) => RecommendationBatch(
    batch: batch,
    generatedAt: generatedAt,
    items: [for (final r in items) r.id == updated.id ? updated : r],
    referral: referral,
  );

  Map<String, dynamic> toJson() => {
    'batch': batch,
    'generated_at': generatedAt?.toIso8601String(),
    'recommendations': [for (final r in items) r.toJson()],
    'referral': referral?.toJson(),
  };
}
