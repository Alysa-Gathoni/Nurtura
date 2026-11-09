/// An activity in Explore (#194), as `/api/children/<id>/activities/`
/// returns it.
class ExploreActivity {
  const ExploreActivity({
    required this.activityId,
    required this.name,
    required this.domain,
    required this.ageRange,
    required this.shortDescription,
    required this.description,
    required this.materials,
    required this.culturalRelevance,
    required this.source,
    required this.sourceUrl,
    required this.saved,
  });

  factory ExploreActivity.fromJson(Map<String, dynamic> json) =>
      ExploreActivity(
        activityId: json['activity_id'] as String,
        name: json['activity_name'] as String,
        domain: json['developmental_domain'] as String,
        ageRange: json['age_range'] as String,
        shortDescription: json['short_description'] as String? ?? '',
        description: json['description'] as String? ?? '',
        materials: json['materials'] as String? ?? '',
        culturalRelevance: json['cultural_relevance'] as String? ?? '',
        source: json['source'] as String? ?? '',
        sourceUrl: json['source_url'] as String? ?? '',
        saved: json['saved'] as bool? ?? false,
      );

  final String activityId, name, domain, ageRange, shortDescription;
  final String description, materials, culturalRelevance, source, sourceUrl;
  final bool saved;

  String get ageLabel => ageRange.replaceAll('-', '–');

  /// What's needed, or null when nothing is ("None").
  String? get materialsNeeded {
    final m = materials.trim();
    if (m.isEmpty || m.toLowerCase().replaceAll('.', '') == 'none') return null;
    return m;
  }

  ExploreActivity withSaved(bool value) => ExploreActivity(
    activityId: activityId,
    name: name,
    domain: domain,
    ageRange: ageRange,
    shortDescription: shortDescription,
    description: description,
    materials: materials,
    culturalRelevance: culturalRelevance,
    source: source,
    sourceUrl: sourceUrl,
    saved: value,
  );
}
