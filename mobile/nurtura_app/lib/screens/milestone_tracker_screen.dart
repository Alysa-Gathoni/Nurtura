import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/child_profile.dart';
import '../models/milestone_tracker.dart';
import '../models/reference_milestone.dart';
import '../services/api_client.dart';
import '../services/milestone_service.dart';
import '../state/auth_state.dart';
import '../state/children_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/domain_style.dart';
import '../widgets/app_card.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';

/// The child's milestones by area, with the weekly Nurtura observation
/// (#192). Tapping a milestone updates its status; "Log another milestone"
/// opens the catalogue picker.
class MilestoneTrackerScreen extends StatefulWidget {
  const MilestoneTrackerScreen({
    super.key,
    required this.child,
    required this.onLogAnother,
  });

  final ChildProfile child;
  final VoidCallback onLogAnother;

  @override
  State<MilestoneTrackerScreen> createState() => _MilestoneTrackerScreenState();
}

/// Friendlier words for the statuses in this screen.
const _statusWords = {
  MilestoneStatus.achieved: 'Achieved',
  MilestoneStatus.emerging: 'Starting',
  MilestoneStatus.notYet: 'Not yet',
};

class _MilestoneTrackerScreenState extends State<MilestoneTrackerScreen> {
  late final MilestoneService _service = MilestoneService(
    context.read<ApiClient>(),
  );
  MilestoneTracker? _tracker;
  NurturaObservation? _observation;
  String? _area;
  String? _error;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final tracker = await _service.tracker(widget.child.id);
      if (!mounted) return;
      setState(() {
        _tracker = tracker;
        _area ??= tracker.areas.keys.isEmpty ? null : tracker.areas.keys.first;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 401) return _sessionEnded();
      setState(() => _error = e.message);
      return;
    } on Object {
      // An answer the app can't read (e.g. an older server).
      if (mounted) setState(() => _error = "Couldn't load the tracker.");
      return;
    }
    // The observation is a bonus: if it fails, the card is left out.
    try {
      final observation = await _service.observation(widget.child.id);
      if (mounted) setState(() => _observation = observation);
    } on Object {
      if (mounted) setState(() => _observation = null);
    }
  }

  Future<void> _sessionEnded() async {
    final auth = context.read<AuthState>();
    Navigator.of(context).popUntil((route) => route.isFirst);
    await auth.sessionExpired();
  }

  Future<void> _update(TrackerMilestone m) async {
    final status = await showModalBottomSheet<MilestoneStatus>(
      context: context,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(m.description, style: AppText.quicksand(size: 19)),
              const SizedBox(height: 4),
              Text(
                'Most often seen by ${m.expectedLabel} (${m.source})',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 12),
              for (final s in MilestoneStatus.values)
                ListTile(
                  key: Key('setStatus_${s.apiValue}'),
                  leading: Icon(_icon(s)),
                  title: Text(_statusWords[s]!),
                  selected: m.status == s,
                  onTap: () => Navigator.of(context).pop(s),
                ),
            ],
          ),
        ),
      ),
    );
    if (status == null || !mounted) return;
    setState(() => _saving = true);
    try {
      await _service.record(
        childId: widget.child.id,
        milestone: m.reference,
        status: status,
      );
      if (!mounted) return;
      // The profile changed, so the Today tab asks for fresh ideas.
      context.read<ChildrenState>().markIdeasOutOfDate(widget.child.id);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          key: const Key('trackerSaved'),
          content: Text(
            'Saved: “${m.description}” is ${_statusWords[status]!.toLowerCase()}. '
            "Today's ideas will update.",
          ),
        ),
      );
      await _load();
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 401) return _sessionEnded();
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final tracker = _tracker;
    if (_error != null && tracker == null) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            MessageBanner.error(_error!, key: const Key('trackerError')),
            const SizedBox(height: 12),
            SecondaryButton(
              label: 'Try again',
              icon: Icons.refresh_rounded,
              onPressed: _load,
            ),
          ],
        ),
      );
    }
    if (tracker == null) {
      return const Center(child: CircularProgressIndicator());
    }
    final name = widget.child.name;
    final items = tracker.areas[_area] ?? const <TrackerMilestone>[];
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        key: const Key('trackerList'),
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        children: [
          if (_observation != null && _observation!.text.isNotEmpty) ...[
            _ObservationCard(_observation!),
            const SizedBox(height: 16),
          ],
          if (tracker.prenatal)
            MessageBanner.info(
              'Milestones start once $name is born. Until then, Today has '
              'ideas for pregnancy.',
              key: const Key('trackerPrenatal'),
            )
          else ...[
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final area in tracker.areas.keys)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        key: Key('trackerArea_$area'),
                        avatar: Icon(
                          DomainStyle.of(area, context.palette).icon,
                          size: 18,
                        ),
                        label: Text(domainLabels[area] ?? area),
                        selected: _area == area,
                        onSelected: (_) => setState(() => _area = area),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 14),
            if (items.isEmpty)
              MessageBanner.info(
                'Nothing due in this area for $name right now.',
                key: const Key('trackerEmpty'),
              ),
            for (final m in items) ...[
              _MilestoneCard(
                milestone: m,
                onTap: _saving ? null : () => _update(m),
              ),
              const SizedBox(height: 10),
            ],
          ],
          const SizedBox(height: 6),
          SecondaryButton(
            key: const Key('logAnotherMilestone'),
            label: 'Log another milestone',
            icon: Icons.add_rounded,
            onPressed: widget.onLogAnother,
          ),
        ],
      ),
    );
  }
}

IconData _icon(MilestoneStatus? s) => switch (s) {
  MilestoneStatus.achieved => Icons.check_circle_rounded,
  MilestoneStatus.emerging => Icons.timelapse_rounded,
  MilestoneStatus.notYet => Icons.radio_button_unchecked_rounded,
  null => Icons.flag_outlined,
};

class _MilestoneCard extends StatelessWidget {
  const _MilestoneCard({required this.milestone, required this.onTap});

  final TrackerMilestone milestone;
  final VoidCallback? onTap;

  String get _subtitle {
    final m = milestone;
    final at = m.observedAtMonths;
    return switch (m.status) {
      MilestoneStatus.achieved => 'Achieved at $at months',
      MilestoneStatus.emerging => 'Starting · noted at $at months',
      MilestoneStatus.notYet =>
        'Not yet · most often seen by ${m.expectedLabel}',
      null when m.due => 'Most often seen by ${m.expectedLabel} · not recorded',
      null => 'Coming up · around ${m.expectedLabel}',
    };
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final m = milestone;
    final (color, background) = switch (m.status) {
      MilestoneStatus.achieved => (p.sage, p.sageSoft),
      MilestoneStatus.emerging => (p.mustard, p.mustardSoft),
      _ => (p.mutedText, p.cardAlt),
    };
    return AppCard(
      key: Key('tracker_${m.key}'),
      onTap: onTap,
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: background,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(_icon(m.status), color: color),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  m.description,
                  style: AppText.nunito(size: 15, weight: FontWeight.w700),
                ),
                const SizedBox(height: 2),
                Text(
                  _subtitle,
                  key: Key('trackerStatus_${m.key}'),
                  style: AppText.nunito(size: 13, color: p.mutedText),
                ),
              ],
            ),
          ),
          Icon(Icons.edit_rounded, size: 18, color: p.mutedText),
        ],
      ),
    );
  }
}

/// "Nurtura observation": a short weekly summary from the child's records.
class _ObservationCard extends StatelessWidget {
  const _ObservationCard(this.observation);

  final NurturaObservation observation;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Container(
      key: const Key('observationCard'),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: p.primary,
        borderRadius: BorderRadius.circular(AppRadii.field),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_awesome_rounded, color: p.onPrimary, size: 20),
              const SizedBox(width: 8),
              Text(
                'Nurtura observation',
                style: AppText.nunito(
                  size: 15,
                  weight: FontWeight.w800,
                  color: p.onPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            observation.text,
            key: const Key('observationText'),
            style: AppText.nunito(size: 14, color: p.onPrimary, height: 1.4),
          ),
        ],
      ),
    );
  }
}
