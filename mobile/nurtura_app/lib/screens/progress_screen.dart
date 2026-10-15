import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../logic/progress.dart';
import '../models/child_profile.dart';
import '../models/reference_milestone.dart';
import '../services/api_client.dart';
import '../services/milestone_service.dart';
import '../state/engagement.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/domain_style.dart';
import '../widgets/app_card.dart';
import '../widgets/buttons.dart';
import '../widgets/gamification.dart';
import '../widgets/message_banner.dart';

/// The child's own milestone record and the caregiver's badges and streak.
///
/// Non-comparative (NFR-15): it shows what has been recorded and celebrated,
/// never how the child compares with norms or other children.
class ProgressScreen extends StatefulWidget {
  const ProgressScreen({super.key, required this.child, this.onRecord});

  final ChildProfile child;

  /// Opens the Milestones tab.
  final VoidCallback? onRecord;

  @override
  State<ProgressScreen> createState() => _ProgressScreenState();
}

class _ProgressScreenState extends State<ProgressScreen> {
  late final MilestoneService _service = MilestoneService(
    context.read<ApiClient>(),
  );
  List<MilestoneObservation>? _history;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    if (widget.child.isExpecting) {
      return setState(() => _history = const []);
    }
    try {
      final history = await _service.history(widget.child.id);
      if (mounted) setState(() => _history = history);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final engagement = context.watch<EngagementState>();
    if (_error != null) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            MessageBanner.error(_error!, key: const Key('progressError')),
            const SizedBox(height: 14),
            SecondaryButton(
              label: 'Try again',
              icon: Icons.refresh_rounded,
              onPressed: _load,
            ),
          ],
        ),
      );
    }
    if (_history == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final summary = summarise(
      _history!,
      streak: engagement.streak,
      bestStreak: engagement.bestStreak,
    );
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        key: const Key('progressList'),
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
        children: [
          _Hero(
            summary: summary,
            child: widget.child,
            onRecord: widget.onRecord,
          ),
          const SizedBox(height: 14),
          _StreakCard(
            streak: engagement.streak,
            best: engagement.bestStreak,
            checkedInToday: engagement.checkedInToday,
          ),
          if (!widget.child.isExpecting) ...[
            const SizedBox(height: 22),
            _SectionTitle(
              'By area',
              'What you’ve recorded for ${widget.child.name}',
            ),
            const SizedBox(height: 10),
            _AreaGrid(areas: summary.areas),
          ],
          const SizedBox(height: 22),
          _SectionTitle(
            'Badges',
            '${summary.unlocked} of ${summary.badges.length} unlocked',
          ),
          const SizedBox(height: 12),
          GridView.count(
            crossAxisCount: 3,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 16,
            crossAxisSpacing: 10,
            childAspectRatio: 0.72,
            children: [for (final b in summary.badges) BadgeTile(badge: b)],
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.title, this.subtitle);

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: AppText.quicksand(size: 20)),
        Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.summary, required this.child, this.onRecord});

  final ProgressSummary summary;
  final ChildProfile child;
  final VoidCallback? onRecord;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final expecting = child.isExpecting;
    return AppCard(
      key: const Key('progressHero'),
      padding: const EdgeInsets.all(18),
      child: Row(
        children: [
          ProgressRing(
            value: summary.badges.isEmpty
                ? 0
                : summary.unlocked / summary.badges.length,
            color: p.mustard,
            size: 78,
            stroke: 9,
            child: Icon(Icons.emoji_events_rounded, color: p.mustard, size: 32),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  expecting
                      ? 'Getting ready'
                      : '${summary.celebrated} milestone'
                            '${summary.celebrated == 1 ? '' : 's'} celebrated',
                  key: const Key('celebratedCount'),
                  style: AppText.quicksand(size: 20),
                ),
                const SizedBox(height: 4),
                Text(
                  expecting
                      ? 'Milestones start once ${child.name} is born. Keep '
                            'your streak going with the pregnancy ideas.'
                      : summary.recorded == 0
                      ? 'Record what ${child.name} can do to start '
                            'collecting badges.'
                      : '${summary.recorded} recorded so far. Every one '
                            'helps us suggest better ideas.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                if (!expecting && onRecord != null) ...[
                  const SizedBox(height: 10),
                  TextButton.icon(
                    key: const Key('recordFromProgress'),
                    onPressed: onRecord,
                    icon: const Icon(Icons.add_task_rounded),
                    label: const Text('Record a milestone'),
                    style: TextButton.styleFrom(
                      foregroundColor: p.primary,
                      padding: EdgeInsets.zero,
                      textStyle: AppText.nunito(
                        size: 14,
                        weight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StreakCard extends StatelessWidget {
  const _StreakCard({
    required this.streak,
    required this.best,
    required this.checkedInToday,
  });

  final int streak;
  final int best;
  final bool checkedInToday;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return AppCard(
      key: const Key('streakCard'),
      color: p.mustardSoft,
      padding: const EdgeInsets.all(16),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(color: p.mustard, shape: BoxShape.circle),
            child: Icon(
              Icons.local_fire_department_rounded,
              color: p.card,
              size: 28,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  streak == 0
                      ? 'Start a streak'
                      : '$streak-day streak${streak >= 3 ? '!' : ''}',
                  style: AppText.quicksand(size: 18, color: p.ink),
                ),
                Text(
                  checkedInToday
                      ? 'You checked today’s ideas. See you tomorrow!'
                      : 'Open today’s ideas to keep it going.',
                  style: AppText.nunito(size: 13, color: p.ink),
                ),
                if (best > 1)
                  Text(
                    'Best: $best days',
                    style: AppText.nunito(
                      size: 12,
                      weight: FontWeight.w700,
                      color: p.mutedText,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AreaGrid extends StatelessWidget {
  const _AreaGrid({required this.areas});

  final List<AreaProgress> areas;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final most = areas.fold(1, (m, a) => a.recorded > m ? a.recorded : m);
    return Wrap(
      spacing: 10,
      runSpacing: 10,
      children: [
        for (final a in areas)
          SizedBox(
            width: (MediaQuery.sizeOf(context).width - 40 - 10) / 2,
            child: AppCard(
              key: Key('area_${a.domain}'),
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  ProgressRing(
                    // Fills with this child's own records, relative to the
                    // area recorded most: never a target or a norm.
                    value: a.recorded / most,
                    color: DomainStyle.of(a.domain, p).color,
                    size: 46,
                    stroke: 5,
                    child: Icon(
                      DomainStyle.of(a.domain, p).icon,
                      size: 20,
                      color: DomainStyle.of(a.domain, p).color,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          domainLabels[a.domain] ?? a.domain,
                          style: AppText.nunito(
                            size: 14,
                            weight: FontWeight.w800,
                          ),
                        ),
                        Text(
                          a.recorded == 0
                              ? 'Nothing yet'
                              : '${a.celebrated} celebrated'
                                    '${a.practising > 0 ? ' · ${a.practising} practising' : ''}',
                          maxLines: 2,
                          style: AppText.nunito(size: 12, color: p.mutedText),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}
