import '../models/reference_milestone.dart';
import '../theme/domain_style.dart';

/// A child's own milestone record, per area. Non-comparative (NFR-15): it
/// counts what the caregiver has recorded and never measures the child
/// against norms or other children.
class AreaProgress {
  const AreaProgress({
    required this.domain,
    required this.celebrated,
    required this.practising,
  });

  final String domain;

  /// Recorded as achieved.
  final int celebrated;

  /// Recorded as emerging or not yet: skills the child is working on.
  final int practising;

  int get recorded => celebrated + practising;
}

class ProgressSummary {
  const ProgressSummary({required this.areas, required this.badges});

  final List<AreaProgress> areas;
  final List<AchievementBadge> badges;

  int get celebrated => areas.fold(0, (sum, a) => sum + a.celebrated);
  int get recorded => areas.fold(0, (sum, a) => sum + a.recorded);
  int get unlocked => badges.where((b) => b.unlocked).length;
}

/// A small reward for using the app, unlocked by the caregiver's own actions.
class AchievementBadge {
  const AchievementBadge({
    required this.id,
    required this.title,
    required this.howTo,
    required this.unlocked,
    required this.icon,
  });

  final String id;
  final String title;

  /// What earns it (shown while locked) or what it celebrates.
  final String howTo;
  final bool unlocked;

  /// A Material icon code point name, resolved by the badge tile.
  final String icon;
}

ProgressSummary summarise(
  List<MilestoneObservation> observations, {
  required int streak,
  required int bestStreak,
}) {
  // The latest observation per milestone counts.
  final latest = <String, MilestoneObservation>{};
  final sorted = [...observations]
    ..sort((a, b) => a.observationDate.compareTo(b.observationDate));
  for (final o in sorted) {
    latest['${o.domain}|${o.description}'] = o;
  }

  final areas = [
    for (final domain in developmentalDomains)
      AreaProgress(
        domain: domain,
        celebrated: latest.values
            .where(
              (o) => o.domain == domain && o.status == MilestoneStatus.achieved,
            )
            .length,
        practising: latest.values
            .where(
              (o) => o.domain == domain && o.status != MilestoneStatus.achieved,
            )
            .length,
      ),
  ];
  final recorded = latest.length;
  final celebrated = areas.fold(0, (sum, a) => sum + a.celebrated);
  final areasTouched = areas.where((a) => a.recorded > 0).length;

  return ProgressSummary(
    areas: areas,
    badges: [
      AchievementBadge(
        id: 'first_step',
        title: 'First step',
        howTo: 'Record your first milestone',
        unlocked: recorded >= 1,
        icon: 'flag',
      ),
      AchievementBadge(
        id: 'celebration',
        title: 'Celebration',
        howTo: 'Record a milestone your child has reached',
        unlocked: celebrated >= 1,
        icon: 'celebration',
      ),
      AchievementBadge(
        id: 'explorer',
        title: 'Explorer',
        howTo: 'Record milestones in 3 different areas',
        unlocked: areasTouched >= 3,
        icon: 'explore',
      ),
      AchievementBadge(
        id: 'keen_observer',
        title: 'Keen observer',
        howTo: 'Record 5 milestones',
        unlocked: recorded >= 5,
        icon: 'visibility',
      ),
      AchievementBadge(
        id: 'streak_3',
        title: '3-day streak',
        howTo: 'Check ideas 3 days in a row',
        unlocked: bestStreak >= 3 || streak >= 3,
        icon: 'fire',
      ),
      AchievementBadge(
        id: 'streak_7',
        title: 'Week of play',
        howTo: 'Check ideas 7 days in a row',
        unlocked: bestStreak >= 7 || streak >= 7,
        icon: 'star',
      ),
    ],
  );
}
