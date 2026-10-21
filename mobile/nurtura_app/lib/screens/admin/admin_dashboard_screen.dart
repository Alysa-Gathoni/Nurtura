import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/admin.dart';
import '../../services/admin_service.dart';
import '../../services/api_client.dart';
import '../../state/auth_state.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_theme.dart';
import '../../theme/domain_style.dart';
import '../../widgets/admin_charts.dart';
import '../../widgets/app_card.dart';
import '../../widgets/buttons.dart';
import '../../widgets/message_banner.dart';
import '../../widgets/segmented_toggle.dart';

/// The administrator's operations overview (#123): use over time, outcomes,
/// system health, work waiting, library coverage and recent activity.
/// Aggregates only; no family is named.
class AdminDashboardScreen extends StatefulWidget {
  const AdminDashboardScreen({super.key, required this.onOpenActivities});

  /// Opens the Activities tab, optionally filtered by status.
  final ValueChanged<String?> onOpenActivities;

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  static const _ranges = [7, 30, 90];

  late final AdminService _service = AdminService(context.read<ApiClient>());
  int _range = 30;
  AdminOverview? _data;
  String? _error;
  bool _updatingIndex = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final data = await _service.overview(days: _range);
      if (mounted) setState(() => _data = data);
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 401) {
        return context.read<AuthState>().sessionExpired();
      }
      setState(() => _error = e.message);
    }
  }

  Future<void> _updateIndex() async {
    setState(() => _updatingIndex = true);
    try {
      final message = await _service.updateSearchIndex();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(message.isEmpty ? 'Search index updated.' : message),
        ),
      );
      await _load();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => _updatingIndex = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final data = _data;
    if (data == null) {
      return _error == null
          ? const Center(child: CircularProgressIndicator())
          : Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  MessageBanner.error(
                    _error!,
                    key: const Key('dashboardError'),
                  ),
                  const SizedBox(height: 12),
                  SecondaryButton(
                    key: const Key('retryButton'),
                    label: 'Try again',
                    icon: Icons.refresh_rounded,
                    onPressed: _load,
                  ),
                ],
              ),
            );
    }
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        key: const Key('adminDashboard'),
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
        children: [
          SegmentedToggle(
            key: const Key('rangeToggle'),
            options: [for (final r in _ranges) '$r days'],
            selected: _ranges.indexOf(_range),
            onChanged: (i) {
              setState(() => _range = _ranges[i]);
              _load();
            },
          ),
          const SizedBox(height: 14),
          _OverviewCard(data: data),
          const SizedBox(height: 14),
          _SummaryCards(data: data),
          const SizedBox(height: 14),
          _OutcomesCard(data: data),
          const SizedBox(height: 14),
          _HealthCard(
            data: data,
            updating: _updatingIndex,
            onUpdateIndex: _updateIndex,
          ),
          const SizedBox(height: 14),
          _WorkCard(data: data, onOpenActivities: widget.onOpenActivities),
          const SizedBox(height: 14),
          _CoverageCard(coverage: data.coverage),
          const SizedBox(height: 14),
          _RecentCard(data: data),
          const SizedBox(height: 14),
          _MostRecommendedCard(
            data: data,
            onOpenActivities: widget.onOpenActivities,
          ),
          const SizedBox(height: 14),
          _RatingsCard(data: data),
          const SizedBox(height: 14),
          _MilestonesCard(data: data),
          const SizedBox(height: 14),
          _AttentionCard(data: data),
          const SizedBox(height: 14),
          Text(
            'Figures are totals across all families; no child or caregiver is '
            'named. Active means a caregiver generated ideas, recorded a '
            'milestone, or marked an activity done or rated it.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}

/// A titled dashboard card.
class _Section extends StatelessWidget {
  const _Section({
    required this.title,
    this.subtitle,
    this.trailing,
    required this.child,
    super.key,
  });

  final String title;
  final String? subtitle;
  final Widget? trailing;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: AppText.quicksand(size: 18)),
                    if (subtitle != null)
                      Text(
                        subtitle!,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                  ],
                ),
              ),
              ?trailing,
            ],
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _OverviewCard extends StatelessWidget {
  const _OverviewCard({required this.data});

  final AdminOverview data;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return _Section(
      key: const Key('overviewCard'),
      title: 'Overview',
      subtitle: 'The last ${data.range} days',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: _BigNumber(
                  value: '${data.trendTotals['ideas'] ?? 0}',
                  label: 'idea batches',
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: _BigNumber(
                  value: '${data.trendTotals['milestones'] ?? 0}',
                  label: 'milestones recorded',
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          TrendChart(dates: data.trendDates, series: data.trend),
          const SizedBox(height: 14),
          Divider(color: p.border, height: 1),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _MiniStat(
                icon: Icons.groups_rounded,
                color: const Color(0xFF2F73B8),
                value: '${data.caregivers}',
                label: 'Caregivers · ${data.activeCaregivers} active this week',
              ),
              _MiniStat(
                icon: Icons.child_care_rounded,
                color: const Color(0xFF7A5A86),
                value: '${data.children}',
                label:
                    'Children · ${data.childrenBorn} born, '
                    '${data.childrenExpecting} expected',
              ),
              _MiniStat(
                icon: Icons.auto_awesome_rounded,
                color: const Color(0xFFB4583A),
                value: '${data.recommended}',
                label: 'Activities recommended',
              ),
              _MiniStat(
                icon: Icons.check_rounded,
                color: const Color(0xFF4F7A44),
                value: '${data.triedShare}%',
                label: 'Tried · ${data.done} done, ${data.partly} partly',
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _BigNumber extends StatelessWidget {
  const _BigNumber({required this.value, required this.label});

  final String value, label;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        value,
        style: AppText.nunito(
          size: 34,
          weight: FontWeight.w800,
          color: context.palette.ink,
        ),
      ),
      Text(label, style: Theme.of(context).textTheme.bodySmall),
    ],
  );
}

class _MiniStat extends StatelessWidget {
  const _MiniStat({
    required this.icon,
    required this.color,
    required this.value,
    required this.label,
  });

  final IconData icon;
  final Color color;
  final String value, label;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 150,
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CircleAvatar(
          radius: 16,
          backgroundColor: color,
          child: Icon(icon, size: 17, color: const Color(0xFFFFF8EF)),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                value,
                style: AppText.nunito(size: 16, weight: FontWeight.w800),
              ),
              Text(label, style: Theme.of(context).textTheme.bodySmall),
            ],
          ),
        ),
      ],
    ),
  );
}

class _SummaryCards extends StatelessWidget {
  const _SummaryCards({required this.data});

  final AdminOverview data;

  static const _cards = [
    ('signups', 'New caregivers', [Color(0xFF245D96), Color(0xFF4A88C7)]),
    ('ideas', 'Idea batches', [Color(0xFF8E4128), Color(0xFFC6694A)]),
    (
      'milestones',
      'Milestones recorded',
      [Color(0xFF5A3F64), Color(0xFF86669A)],
    ),
    ('feedback', 'Feedback received', [Color(0xFF3D6234), Color(0xFF5F8C53)]),
  ];

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 12,
      crossAxisSpacing: 12,
      childAspectRatio: 1.35,
      children: [
        for (final (key, label, colours) in _cards)
          Container(
            key: Key('stat_$key'),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: colours,
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: AppText.nunito(
                    size: 13,
                    weight: FontWeight.w800,
                    color: Colors.white,
                  ),
                ),
                const Spacer(),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Expanded(child: Sparkline(data.spark[key] ?? const [])),
                    const SizedBox(width: 8),
                    Text(
                      '${data.sparkTotals[key] ?? 0}',
                      style: AppText.nunito(
                        size: 28,
                        weight: FontWeight.w800,
                        color: Colors.white,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  'Last ${data.sparkDays} days',
                  style: AppText.nunito(
                    size: 11.5,
                    color: Colors.white.withValues(alpha: 0.9),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _OutcomesCard extends StatelessWidget {
  const _OutcomesCard({required this.data});

  final AdminOverview data;

  @override
  Widget build(BuildContext context) {
    final c = ChartColors.of(context);
    final p = context.palette;
    int share(int n) =>
        data.recommended == 0 ? 0 : (100 * n / data.recommended).round();
    final parts = [
      ('Done', data.done, c.done),
      ('Partly done', data.partly, c.partly),
      ('Not marked yet', data.notMarked, p.border),
    ];
    return _Section(
      key: const Key('outcomesCard'),
      title: 'Recommended activities',
      subtitle: 'What families did with the ${data.recommended} suggested',
      child: Column(
        children: [
          DonutChart(
            parts: [
              for (final (_, n, colour) in parts) (value: n, color: colour),
            ],
            centre: '${data.triedShare}%',
            caption: 'tried',
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              for (final (label, n, colour) in parts)
                Expanded(
                  child: Column(
                    children: [
                      Text(
                        '${share(n)}%',
                        style: AppText.nunito(
                          size: 18,
                          weight: FontWeight.w800,
                        ),
                      ),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          chartSwatch(colour),
                          const SizedBox(width: 4),
                          Flexible(
                            child: Text(
                              label,
                              textAlign: TextAlign.center,
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _HealthCard extends StatelessWidget {
  const _HealthCard({
    required this.data,
    required this.updating,
    required this.onUpdateIndex,
  });

  final AdminOverview data;
  final bool updating;
  final VoidCallback onUpdateIndex;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return _Section(
      key: const Key('healthCard'),
      title: 'System health',
      subtitle: 'Checked each time this page loads',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final h in data.health)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Row(
                children: [
                  _StatusIcon(status: h.status),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          h.title,
                          style: AppText.nunito(
                            size: 14.5,
                            weight: FontWeight.w800,
                          ),
                        ),
                        Text(
                          h.detail,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 6),
                  _StatusLabel(status: h.status),
                ],
              ),
            ),
          if (data.searchIndexOutOfDate)
            PrimaryButton(
              key: const Key('updateIndexButton'),
              label: 'Update search index',
              icon: Icons.manage_search_rounded,
              loading: updating,
              onPressed: onUpdateIndex,
            ),
          if (data.searchIndexOutOfDate)
            Padding(
              padding: const EdgeInsets.only(top: 6),
              child: Text(
                'Makes newly Published activities searchable. The first time can take about 15 seconds.',
                style: AppText.nunito(size: 12, color: p.mutedText),
              ),
            ),
        ],
      ),
    );
  }
}

({Color fg, Color bg, IconData icon, String label}) _statusStyle(
  BuildContext context,
  String status,
) {
  final p = context.palette;
  return switch (status) {
    'good' => (
      fg: p.sage,
      bg: p.sageSoft,
      icon: Icons.check_rounded,
      label: 'OK',
    ),
    'warning' => (
      fg: p.mustard,
      bg: p.mustardSoft,
      icon: Icons.priority_high_rounded,
      label: 'Check',
    ),
    _ => (fg: p.rose, bg: p.roseSoft, icon: Icons.close_rounded, label: 'Fix'),
  };
}

class _StatusIcon extends StatelessWidget {
  const _StatusIcon({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final s = _statusStyle(context, status);
    return CircleAvatar(
      radius: 15,
      backgroundColor: s.bg,
      child: Icon(s.icon, size: 17, color: s.fg),
    );
  }
}

class _StatusLabel extends StatelessWidget {
  const _StatusLabel({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final s = _statusStyle(context, status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: s.bg,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        s.label,
        style: AppText.nunito(size: 11.5, weight: FontWeight.w900, color: s.fg),
      ),
    );
  }
}

class _WorkCard extends StatelessWidget {
  const _WorkCard({required this.data, required this.onOpenActivities});

  final AdminOverview data;
  final ValueChanged<String?> onOpenActivities;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final c = ChartColors.of(context);
    return _Section(
      key: const Key('workCard'),
      title: 'Work waiting',
      subtitle: 'Content that needs an administrator',
      child: Column(
        children: [
          _WorkRow(
            key: const Key('workReview'),
            count: data.drafts + data.underReview,
            title: 'Activities to review',
            detail: '${data.drafts} draft · ${data.underReview} under review',
            onTap: () => onOpenActivities(
              data.underReview > 0 ? 'under_review' : 'draft',
            ),
          ),
          _WorkRow(
            count: data.unverifiedMilestones,
            title: 'Milestones to verify',
            detail:
                '${data.verifiedShare}% of ${data.catalogueMilestones} checked '
                'against the source (in the web admin)',
            extra: ClipRRect(
              borderRadius: BorderRadius.circular(999),
              child: LinearProgressIndicator(
                value: data.verifiedShare / 100,
                minHeight: 6,
                color: c.done,
                backgroundColor: p.cardAlt,
              ),
            ),
          ),
          _WorkRow(
            count: data.coverage.gaps,
            title: 'Library gaps',
            detail: 'Area and age with no Published activity',
          ),
        ],
      ),
    );
  }
}

class _WorkRow extends StatelessWidget {
  const _WorkRow({
    super.key,
    required this.count,
    required this.title,
    required this.detail,
    this.extra,
    this.onTap,
  });

  final int count;
  final String title, detail;
  final Widget? extra;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          children: [
            SizedBox(
              width: 52,
              child: Text(
                '$count',
                textAlign: TextAlign.center,
                style: AppText.nunito(size: 22, weight: FontWeight.w800),
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    title,
                    style: AppText.nunito(size: 14.5, weight: FontWeight.w800),
                  ),
                  Text(detail, style: Theme.of(context).textTheme.bodySmall),
                  if (extra != null) ...[const SizedBox(height: 6), extra!],
                ],
              ),
            ),
            if (onTap != null)
              Icon(
                Icons.chevron_right_rounded,
                color: context.palette.mutedText,
              ),
          ],
        ),
      ),
    );
  }
}

class _CoverageCard extends StatelessWidget {
  const _CoverageCard({required this.coverage});

  final Coverage coverage;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final heat = ChartColors.of(context).ideas;
    final top = coverage.rows
        .expand((r) => r.counts)
        .fold(0, (a, b) => a > b ? a : b);
    return _Section(
      key: const Key('coverageCard'),
      title: 'Library coverage',
      subtitle:
          'Published activities by area and age in months · plus '
          '${coverage.prenatal} for pregnancy',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Table(
            columnWidths: const {0: FlexColumnWidth(2.2)},
            defaultVerticalAlignment: TableCellVerticalAlignment.middle,
            children: [
              TableRow(
                children: [
                  const SizedBox(),
                  for (final age in coverage.ages)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Text(
                        age,
                        textAlign: TextAlign.center,
                        style: AppText.nunito(
                          size: 10.5,
                          weight: FontWeight.w800,
                          color: p.mutedText,
                        ),
                      ),
                    ),
                ],
              ),
              for (final row in coverage.rows)
                TableRow(
                  children: [
                    Text(
                      domainLabels[row.label] ?? row.label,
                      style: AppText.nunito(
                        size: 12.5,
                        weight: FontWeight.w700,
                      ),
                    ),
                    for (final n in row.counts)
                      Padding(
                        padding: const EdgeInsets.all(2),
                        child: Container(
                          height: 28,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: n == 0
                                ? Colors.transparent
                                : heat.withValues(
                                    alpha:
                                        0.12 + 0.55 * n / (top == 0 ? 1 : top),
                                  ),
                            borderRadius: BorderRadius.circular(6),
                            border: n == 0
                                ? Border.all(color: p.rose, width: 1.5)
                                : null,
                          ),
                          child: Text(
                            '$n',
                            style: AppText.nunito(
                              size: 12,
                              weight: FontWeight.w800,
                              color: n == 0 ? p.rose : p.ink,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Darker means more activities; an outlined 0 is a gap.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }
}

class _RecentCard extends StatelessWidget {
  const _RecentCard({required this.data});

  final AdminOverview data;

  static const _kindColours = {
    'signup': Color(0xFF2F73B8),
    'ideas': Color(0xFFB4583A),
    'milestone': Color(0xFF7A5A86),
    'done': Color(0xFF4F7A44),
    'feedback': Color(0xFFCF9B33),
  };

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return _Section(
      key: const Key('recentCard'),
      title: 'Recent activity',
      subtitle: 'Newest first; families are never named',
      child: data.events.isEmpty
          ? Text(
              'Nothing has happened yet.',
              style: Theme.of(context).textTheme.bodySmall,
            )
          : Column(
              children: [
                for (final e in data.events)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Padding(
                          padding: const EdgeInsets.only(top: 3),
                          child: CircleAvatar(
                            radius: 6,
                            backgroundColor:
                                _kindColours[e.kind] ?? p.mutedText,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                e.title,
                                style: AppText.nunito(
                                  size: 14,
                                  weight: FontWeight.w800,
                                ),
                              ),
                              if (e.detail.isNotEmpty)
                                Text(
                                  e.detail,
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                            ],
                          ),
                        ),
                        Text(
                          _ago(e.when),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
              ],
            ),
    );
  }
}

/// "5 min ago", "3 h ago", "2 d ago".
String _ago(DateTime when) {
  final d = DateTime.now().difference(when.toLocal());
  if (d.inMinutes < 1) return 'just now';
  if (d.inHours < 1) return '${d.inMinutes} min ago';
  if (d.inDays < 1) return '${d.inHours} h ago';
  return '${d.inDays} d ago';
}

class _MostRecommendedCard extends StatelessWidget {
  const _MostRecommendedCard({
    required this.data,
    required this.onOpenActivities,
  });

  final AdminOverview data;
  final ValueChanged<String?> onOpenActivities;

  @override
  Widget build(BuildContext context) {
    return _Section(
      key: const Key('mostRecommendedCard'),
      title: 'Most recommended',
      subtitle: 'How often each was suggested, tried and rated',
      trailing: TextButton(
        onPressed: () => onOpenActivities(null),
        child: const Text('All activities'),
      ),
      child: data.mostRecommended.isEmpty
          ? Text(
              'Nothing recommended yet.',
              style: Theme.of(context).textTheme.bodySmall,
            )
          : Column(
              children: [
                for (final a in data.mostRecommended)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: Row(
                      children: [
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                a.name,
                                style: AppText.nunito(
                                  size: 14,
                                  weight: FontWeight.w800,
                                ),
                              ),
                              Text(
                                '${a.activityId} · ${domainLabels[a.domain] ?? a.domain}',
                                style: Theme.of(context).textTheme.bodySmall,
                              ),
                            ],
                          ),
                        ),
                        _Figure(value: '${a.times}', label: 'given'),
                        _Figure(value: '${a.doneShare}%', label: 'done'),
                        _Figure(
                          value: a.average == null ? '–' : '${a.average}★',
                          label: 'rating',
                        ),
                      ],
                    ),
                  ),
              ],
            ),
    );
  }
}

class _Figure extends StatelessWidget {
  const _Figure({required this.value, required this.label});

  final String value, label;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 52,
    child: Column(
      children: [
        Text(value, style: AppText.nunito(size: 14, weight: FontWeight.w800)),
        Text(label, style: Theme.of(context).textTheme.bodySmall),
      ],
    ),
  );
}

class _RatingsCard extends StatelessWidget {
  const _RatingsCard({required this.data});

  final AdminOverview data;

  @override
  Widget build(BuildContext context) {
    final c = ChartColors.of(context);
    final p = context.palette;
    final top = data.ratingsByStar.fold(0, (a, b) => a > b ? a : b);
    return _Section(
      key: const Key('ratingsCard'),
      title: 'Ratings',
      subtitle: data.ratingsCount == 0
          ? 'No ratings yet'
          : 'Average ${data.ratingsAverage} from ${data.ratingsCount} '
                'rating${data.ratingsCount == 1 ? '' : 's'}',
      child: data.ratingsCount == 0
          ? Text(
              'Ratings appear here once caregivers rate activities.',
              style: Theme.of(context).textTheme.bodySmall,
            )
          : SizedBox(
              height: 140,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  for (var i = 0; i < 5; i++)
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          Text(
                            '${data.ratingsByStar[i]}',
                            style: AppText.nunito(
                              size: 12,
                              weight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Container(
                            width: 22,
                            height: top == 0
                                ? 0
                                : 90 * data.ratingsByStar[i] / top,
                            decoration: BoxDecoration(
                              color: c.ideas,
                              borderRadius: const BorderRadius.vertical(
                                top: Radius.circular(4),
                              ),
                            ),
                          ),
                          Container(height: 1, color: p.border),
                          const SizedBox(height: 4),
                          Text(
                            '${i + 1}★',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}

class _MilestonesCard extends StatelessWidget {
  const _MilestonesCard({required this.data});

  final AdminOverview data;

  @override
  Widget build(BuildContext context) {
    final c = ChartColors.of(context);
    Color colour(String status) => switch (status) {
      'achieved' => c.done,
      'emerging' => c.partly,
      _ => c.notYet,
    };
    return _Section(
      key: const Key('milestonesCard'),
      title: 'Milestones recorded',
      subtitle: '${data.milestonesTotal} records, by status',
      child: data.milestonesTotal == 0
          ? Text(
              'No milestones recorded yet.',
              style: Theme.of(context).textTheme.bodySmall,
            )
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: SizedBox(
                    height: 16,
                    child: Row(
                      children: [
                        for (final m in data.milestonesByStatus)
                          if (m.count > 0)
                            Expanded(
                              flex: m.count,
                              child: Container(
                                margin: const EdgeInsets.only(right: 2),
                                color: colour(m.status),
                              ),
                            ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 14,
                  runSpacing: 4,
                  children: [
                    for (final m in data.milestonesByStatus)
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          chartSwatch(colour(m.status)),
                          const SizedBox(width: 6),
                          Text('${m.label} ', style: AppText.nunito(size: 13)),
                          Text(
                            '${m.count}',
                            style: AppText.nunito(
                              size: 13,
                              weight: FontWeight.w800,
                            ),
                          ),
                        ],
                      ),
                  ],
                ),
              ],
            ),
    );
  }
}

class _AttentionCard extends StatelessWidget {
  const _AttentionCard({required this.data});

  final AdminOverview data;

  @override
  Widget build(BuildContext context) {
    return _Section(
      key: const Key('attentionCard'),
      title: 'Needs attention',
      subtitle: 'Average rating of ${data.needsAttentionAt} or below',
      child: data.needsAttention.isEmpty
          ? Text(
              'Nothing rated that low.',
              style: Theme.of(context).textTheme.bodySmall,
            )
          : Column(
              children: [
                for (final a in data.needsAttention)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    dense: true,
                    title: Text(
                      a.name,
                      style: AppText.nunito(size: 14, weight: FontWeight.w800),
                    ),
                    subtitle: Text(a.activityId),
                    trailing: Text(
                      '${a.average}★ · ${a.ratings}',
                      style: AppText.nunito(size: 13, weight: FontWeight.w800),
                    ),
                  ),
              ],
            ),
    );
  }
}
