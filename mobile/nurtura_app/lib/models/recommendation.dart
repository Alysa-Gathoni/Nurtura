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

/// How an activity went (#175). The API values are the enum's [value]s.
enum FeedbackOutcome {
  wentWell('went_well', 'Went well'),
  partly('partly', 'Partly'),
  didntWork('didnt_work', "Didn't work");

  const FeedbackOutcome(this.value, this.label);
  final String value;
  final String label;

  static FeedbackOutcome? fromValue(String? value) {
    for (final o in values) {
      if (o.value == value) return o;
    }
    return null;
  }
}

/// What got in the way of an activity (#175), in the order shown.
enum FeedbackIssue {
  tooHard('too_hard', 'Too hard'),
  tooEasy('too_easy', 'Too easy'),
  notInterested('not_interested', "My child wasn't interested"),
  noMaterials('no_materials', "I didn't have the materials"),
  noTime('no_time', 'Not enough time'),
  childUpset('child_upset', 'My child got upset');

  const FeedbackIssue(this.value, this.label);
  final String value;
  final String label;

  static FeedbackIssue? fromValue(String value) {
    for (final i in values) {
      if (i.value == value) return i;
    }
    return null;
  }
}

/// The caregiver's feedback on a recommendation (FR-15): how it went and
/// what got in the way (#175), a rating and a comment.
class ActivityFeedback {
  const ActivityFeedback({
    required this.rating,
    required this.comment,
    required this.submittedAt,
    this.outcome,
    this.issues = const [],
  });

  factory ActivityFeedback.fromJson(Map<String, dynamic> json) =>
      ActivityFeedback(
        rating: json['rating'] as int,
        comment: json['comment'] as String? ?? '',
        submittedAt: DateTime.parse(json['date_submitted'] as String),
        outcome: FeedbackOutcome.fromValue(json['outcome'] as String?),
        // Values this app version doesn't know are skipped.
        issues: [
          for (final v in json['issues'] as List? ?? const [])
            ?FeedbackIssue.fromValue(v as String),
        ],
      );

  final int rating;
  final String comment;
  final DateTime submittedAt;

  /// Null on feedback given before the question was asked.
  final FeedbackOutcome? outcome;
  final List<FeedbackIssue> issues;

  Map<String, dynamic> toJson() => {
    'rating': rating,
    'comment': comment,
    'outcome': outcome?.value ?? '',
    'issues': [for (final i in issues) i.value],
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
    this.pinned = false,
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
    pinned: json['pinned'] as bool? ?? false,
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

  /// Chosen by the caregiver from the options after feedback (#177).
  final bool pinned;
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
    'pinned': pinned,
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
    pinned: pinned,
    completion: completion == null ? this.completion : completion(),
    feedback: feedback ?? this.feedback,
  );
}

/// Another activity offered after feedback (#177): what it answers, why,
/// and the activity itself.
class FeedbackOption {
  const FeedbackOption({
    required this.reason,
    required this.title,
    required this.why,
    required this.tip,
    required this.activityId,
    required this.activityName,
    required this.domain,
    required this.ageRange,
    required this.shortDescription,
  });

  factory FeedbackOption.fromJson(Map<String, dynamic> json) {
    final a = json['activity'] as Map<String, dynamic>;
    return FeedbackOption(
      reason: json['reason'] as String,
      title: json['title'] as String,
      why: json['why'] as String? ?? '',
      tip: json['tip'] as String? ?? '',
      activityId: a['activity_id'] as String,
      activityName: a['activity_name'] as String,
      domain: a['developmental_domain'] as String,
      ageRange: a['age_range'] as String,
      shortDescription: a['short_description'] as String? ?? '',
    );
  }

  final String reason;
  final String title;
  final String why;
  final String tip;
  final String activityId;
  final String activityName;
  final String domain;
  final String ageRange;
  final String shortDescription;

  String get ageLabel => ageRange.replaceAll('-', '–');
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
