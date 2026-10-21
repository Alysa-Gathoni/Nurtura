/// Data for the administrator screens (#123), from `/api/admin/`.
library;

List<int> _ints(Object? value) => [
  for (final v in value as List? ?? const []) (v as num).toInt(),
];

int _int(Object? value) => (value as num?)?.toInt() ?? 0;

/// The operations overview (`GET /api/admin/overview/`).
class AdminOverview {
  AdminOverview.fromJson(Map<String, dynamic> json)
    : range = _int(json['range']),
      ranges = _ints(json['ranges']),
      caregivers = _int(json['people']['caregivers']),
      activeCaregivers = _int(json['people']['active_caregivers']),
      children = _int(json['people']['children']),
      childrenBorn = _int(json['people']['children_born']),
      childrenExpecting = _int(json['people']['children_expecting']),
      trendDates = [
        for (final d in json['trend']['dates'] as List)
          DateTime.parse(d as String),
      ],
      trend = {
        for (final e in (json['trend']['series'] as Map).entries)
          e.key as String: _ints(e.value),
      },
      trendTotals = {
        for (final e in (json['trend']['totals'] as Map).entries)
          e.key as String: _int(e.value),
      },
      sparkDays = _int(json['spark']['days']),
      spark = {
        for (final e in (json['spark']['series'] as Map).entries)
          e.key as String: _ints(e.value),
      },
      sparkTotals = {
        for (final e in (json['spark']['totals'] as Map).entries)
          e.key as String: _int(e.value),
      },
      recommended = _int(json['outcomes']['recommended']),
      done = _int(json['outcomes']['done']),
      partly = _int(json['outcomes']['partly']),
      notMarked = _int(json['outcomes']['not_marked']),
      triedShare = _int(json['outcomes']['tried_share']),
      ratingsCount = _int(json['ratings']['count']),
      ratingsAverage = (json['ratings']['average'] as num?)?.toDouble(),
      ratingsByStar = _ints(json['ratings']['by_star']),
      milestonesTotal = _int(json['milestones']['total']),
      milestonesByStatus = [
        for (final m in json['milestones']['by_status'] as List)
          (
            status: m['status'] as String,
            label: m['label'] as String,
            count: _int(m['count']),
          ),
      ],
      needsAttention = [
        for (final a in json['needs_attention'] as List)
          RatedActivity.fromJson(a),
      ],
      needsAttentionAt = (json['needs_attention_at'] as num).toDouble(),
      health = [
        for (final h in json['health'] as List)
          (
            status: h['status'] as String,
            title: h['title'] as String,
            detail: h['detail'] as String,
          ),
      ],
      drafts = _int(json['waiting']['drafts']),
      underReview = _int(json['waiting']['under_review']),
      unverifiedMilestones = _int(json['waiting']['unverified']),
      catalogueMilestones = _int(json['waiting']['milestones_total']),
      verifiedShare = _int(json['waiting']['verified_share']),
      coverage = Coverage.fromJson(json['coverage'] as Map<String, dynamic>),
      events = [
        for (final e in json['events'] as List)
          (
            when: DateTime.parse(e['when'] as String),
            kind: e['kind'] as String,
            title: e['title'] as String,
            detail: e['detail'] as String? ?? '',
          ),
      ],
      mostRecommended = [
        for (final a in json['most_recommended'] as List)
          RecommendedActivity.fromJson(a as Map<String, dynamic>),
      ];

  final int range;
  final List<int> ranges;
  final int caregivers,
      activeCaregivers,
      children,
      childrenBorn,
      childrenExpecting;
  final List<DateTime> trendDates;

  /// Daily counts: `ideas`, `milestones`, `feedback`.
  final Map<String, List<int>> trend;
  final Map<String, int> trendTotals;
  final int sparkDays;

  /// Daily counts for the summary cards: `signups`, `ideas`, `milestones`,
  /// `feedback`.
  final Map<String, List<int>> spark;
  final Map<String, int> sparkTotals;
  final int recommended, done, partly, notMarked, triedShare;
  final int ratingsCount;
  final double? ratingsAverage;

  /// Counts of 1 to 5 stars.
  final List<int> ratingsByStar;
  final int milestonesTotal;
  final List<({String status, String label, int count})> milestonesByStatus;
  final List<RatedActivity> needsAttention;
  final double needsAttentionAt;

  /// `status` is `good`, `warning` or `alert`.
  final List<({String status, String title, String detail})> health;
  final int drafts, underReview, unverifiedMilestones, catalogueMilestones;
  final int verifiedShare;
  final Coverage coverage;
  final List<({DateTime when, String kind, String title, String detail})>
  events;
  final List<RecommendedActivity> mostRecommended;

  bool get searchIndexOutOfDate => health.any(
    (h) => h.title.startsWith('Search index') && h.status != 'good',
  );
}

class RatedActivity {
  RatedActivity.fromJson(Map<String, dynamic> json)
    : id = _int(json['pk']),
      activityId = json['activity_id'] as String,
      name = json['name'] as String,
      average = (json['average'] as num).toDouble(),
      ratings = _int(json['ratings']);

  final int id;
  final String activityId, name;
  final double average;
  final int ratings;
}

class RecommendedActivity {
  RecommendedActivity.fromJson(Map<String, dynamic> json)
    : id = _int(json['pk']),
      activityId = json['activity_id'] as String,
      name = json['name'] as String,
      domain = json['domain'] as String,
      times = _int(json['times']),
      doneShare = _int(json['done_share']),
      average = (json['average'] as num?)?.toDouble(),
      status = json['status_key'] as String,
      statusLabel = json['status'] as String;

  final int id;
  final String activityId, name, domain;
  final int times, doneShare;
  final double? average;
  final String status, statusLabel;
}

/// Published activities by area (rows) and age (columns).
class Coverage {
  Coverage.fromJson(Map<String, dynamic> json)
    : ages = [for (final a in json['ages'] as List) a as String],
      rows = [
        for (final r in json['rows'] as List)
          (
            label: r['label'] as String,
            counts: [for (final c in r['cells'] as List) _int(c['count'])],
          ),
      ],
      gaps = _int(json['gaps']),
      prenatal = _int(json['prenatal']);

  final List<String> ages;
  final List<({String label, List<int> counts})> rows;
  final int gaps, prenatal;
}

/// An activity as administrators see and edit it.
class AdminActivity {
  AdminActivity.fromJson(Map<String, dynamic> json)
    : id = _int(json['id']),
      activityId = json['activity_id'] as String,
      name = json['activity_name'] as String,
      domain = json['developmental_domain'] as String,
      ageRange = json['age_range'] as String,
      goal = json['developmental_goal'] as String? ?? '',
      materials = json['materials'] as String? ?? '',
      difficulty = json['difficulty_level'] as String,
      description = json['description'] as String? ?? '',
      culturalRelevance = json['cultural_relevance'] as String? ?? '',
      plainAim = json['plain_aim'] as String? ?? '',
      source = json['source'] as String,
      sourceUrl = json['source_url'] as String? ?? '',
      status = json['content_status'] as String,
      statusLabel = json['status_label'] as String? ?? '',
      timesRecommended = _int(json['times_recommended']),
      feedbackCount = _int(json['feedback_count']),
      averageRating = (json['average_rating'] as num?)?.toDouble(),
      searchable = json['searchable'] as bool? ?? false;

  final int id;
  final String activityId, name, domain, ageRange, goal, materials;
  final String difficulty, description, culturalRelevance, plainAim;
  final String source, sourceUrl, status, statusLabel;
  final int timesRecommended, feedbackCount;
  final double? averageRating;
  final bool searchable;
}

class Choice {
  const Choice(this.value, this.label);

  final String value, label;
}

/// Allowed values for the activity form and the review workflow.
class AdminChoices {
  AdminChoices.fromJson(Map<String, dynamic> json)
    : domains = _choices(json['domains']),
      ageRanges = _choices(json['age_ranges']),
      difficultyLevels = _choices(json['difficulty_levels']),
      sources = _choices(json['sources']),
      statuses = _choices(json['statuses']),
      transitions = {
        for (final e in (json['transitions'] as Map).entries)
          e.key as String: [for (final t in e.value as List) t as String],
      };

  static List<Choice> _choices(Object? value) => [
    for (final c in value as List)
      Choice(c['value'] as String, c['label'] as String),
  ];

  final List<Choice> domains, ageRanges, difficultyLevels, sources, statuses;

  /// Where each status may move next.
  final Map<String, List<String>> transitions;

  String statusLabel(String value) => statuses
      .firstWhere((c) => c.value == value, orElse: () => Choice(value, value))
      .label;
}

/// One rating and comment, against its activity.
class AdminFeedback {
  AdminFeedback.fromJson(Map<String, dynamic> json)
    : id = _int(json['id']),
      rating = _int(json['rating']),
      comment = json['comment'] as String? ?? '',
      submitted = DateTime.parse(json['date_submitted'] as String),
      completion = json['completion'] as String?,
      activityId = _int(json['activity']['id']),
      activityCode = json['activity']['activity_id'] as String,
      activityName = json['activity']['name'] as String,
      domain = json['activity']['domain'] as String,
      ageRange = json['activity']['age_range'] as String;

  final int id, rating;
  final String comment;
  final DateTime submitted;

  /// `completed`, `partially_completed` or null (not marked).
  final String? completion;
  final int activityId;
  final String activityCode, activityName, domain, ageRange;
}
