import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/child_profile.dart';
import '../models/reference_milestone.dart';
import '../services/api_client.dart';
import '../services/milestone_service.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/domain_style.dart';
import '../utils/dates.dart';
import '../widgets/app_card.dart';
import '../widgets/app_text_field.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';
import '../widgets/nurtura_app_bar.dart';
import '../widgets/pill_chip.dart';

/// Records a milestone for a child by picking it from the guideline
/// catalogue (never free text, since only catalogue milestones have an
/// expected age the rule engine can use).
class MilestoneScreen extends StatefulWidget {
  const MilestoneScreen({
    super.key,
    required this.child,
    this.justCreated = false,
  });

  final ChildProfile child;

  /// Shows a "profile saved" confirmation at the top.
  final bool justCreated;

  @override
  State<MilestoneScreen> createState() => _MilestoneScreenState();
}

class _MilestoneScreenState extends State<MilestoneScreen> {
  static const _debounce = Duration(milliseconds: 300);

  late final MilestoneService _service = MilestoneService(
    context.read<ApiClient>(),
  );
  final _search = TextEditingController();
  Timer? _debounceTimer;
  int _requestId = 0;

  String? _domain;
  List<ReferenceMilestone> _results = const [];
  bool _loading = false;
  ApiException? _loadError;

  ReferenceMilestone? _selected;
  MilestoneStatus? _status;
  bool _submitting = false;
  ApiException? _submitError;
  RecordedMilestone? _recorded;

  @override
  void initState() {
    super.initState();
    if (!widget.child.isExpecting) _load();
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _search.dispose();
    super.dispose();
  }

  void _onSearchChanged(String _) {
    _debounceTimer?.cancel();
    _debounceTimer = Timer(_debounce, _load);
  }

  void _setDomain(String? domain) {
    setState(() => _domain = domain);
    _load();
  }

  Future<void> _load() async {
    final requestId = ++_requestId;
    setState(() {
      _loading = true;
      _loadError = null;
    });
    try {
      final results = await _service.search(
        search: _search.text,
        domain: _domain,
      );
      if (!mounted || requestId != _requestId) return; // a newer search won
      final age = monthsBetween(widget.child.dateOfBirth, today()).toDouble();
      // Milestones closest to the child's age first; ties by age, then key,
      // so the order is stable between searches.
      results.sort((a, b) {
        final byDistance = (a.expectedAgeMonths - age).abs().compareTo(
          (b.expectedAgeMonths - age).abs(),
        );
        if (byDistance != 0) return byDistance;
        final byAge = a.expectedAgeMonths.compareTo(b.expectedAgeMonths);
        return byAge != 0 ? byAge : a.key.compareTo(b.key);
      });
      setState(() => _results = results);
    } on ApiException catch (e) {
      if (mounted && requestId == _requestId) setState(() => _loadError = e);
    } finally {
      if (mounted && requestId == _requestId) setState(() => _loading = false);
    }
  }

  void _select(ReferenceMilestone milestone) {
    setState(() {
      _selected = _selected?.id == milestone.id ? null : milestone;
      _status = null;
      _submitError = null;
    });
  }

  Future<void> _submit() async {
    if (_submitting || _selected == null || _status == null) return;
    setState(() {
      _submitting = true;
      _submitError = null;
    });
    try {
      final recorded = await _service.record(
        childId: widget.child.id,
        milestone: _selected!,
        status: _status!,
      );
      if (mounted) setState(() => _recorded = recorded);
    } on ApiException catch (e) {
      if (mounted) setState(() => _submitError = e);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  void _recordAnother() {
    setState(() {
      _recorded = null;
      _selected = null;
      _status = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: const NurturaAppBar(title: 'Record a milestone'),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: _recorded != null
                ? _Confirmation(
                    child: widget.child,
                    recorded: _recorded!,
                    onRecordAnother: _recordAnother,
                  )
                : widget.child.isExpecting
                ? _prenatalMessage()
                : _picker(),
          ),
        ),
      ),
    );
  }

  Widget _savedBanner() => MessageBanner.success(
    "${widget.child.name}'s profile is saved.",
    key: const Key('profileSavedBanner'),
  );

  Widget _prenatalMessage() {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (widget.justCreated) ...[
            _savedBanner(),
            const SizedBox(height: 12),
          ],
          MessageBanner.info(
            'Milestone tracking starts once ${widget.child.name} is born '
            '(due ${formatDate(widget.child.dateOfBirth)}).',
            key: const Key('prenatalMessage'),
          ),
          const SizedBox(height: 16),
          SecondaryButton(
            label: 'Back to your children',
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }

  Widget _picker() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 18, 20, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (widget.justCreated) ...[
                _savedBanner(),
                const SizedBox(height: 12),
              ],
              Text(
                '${widget.child.name} · ${widget.child.ageDescription}',
                style: AppText.quicksand(size: 20, color: AppColors.tealDeep),
              ),
              const SizedBox(height: 2),
              Text(
                'Find a milestone from the CDC and WHO checklists, then tell '
                'us how ${widget.child.name} is doing.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 14),
              AppTextField(
                key: const Key('milestoneSearchField'),
                label: 'Search milestones',
                hint: 'e.g. waves, crawls, words',
                controller: _search,
                prefixIcon: Icons.search_rounded,
                textInputAction: TextInputAction.search,
                onChanged: _onSearchChanged,
              ),
              const SizedBox(height: 12),
            ],
          ),
        ),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Row(
            children: [
              PillChip(
                key: const Key('domain_All'),
                label: 'All',
                color: AppColors.tealDeep,
                background: AppColors.mint,
                selected: _domain == null,
                onTap: () => _setDomain(null),
              ),
              for (final domain in developmentalDomains)
                if (domain !=
                    'Sensory') // no Sensory milestones in the guidelines
                  Padding(
                    padding: const EdgeInsets.only(left: 8),
                    child: DomainChip(
                      domain,
                      key: Key('domain_$domain'),
                      selected: _domain == domain,
                      onTap: () => _setDomain(domain),
                    ),
                  ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        Expanded(child: _resultsList()),
        if (_selected != null) _statusPanel(),
      ],
    );
  }

  Widget _resultsList() {
    if (_loadError != null) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            MessageBanner.error(_loadError!.message),
            const SizedBox(height: 12),
            SecondaryButton(
              key: const Key('retrySearchButton'),
              label: 'Try again',
              icon: Icons.refresh_rounded,
              onPressed: _load,
            ),
          ],
        ),
      );
    }
    if (_loading && _results.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_results.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Text(
          'No milestones match "${_search.text.trim()}". Try another word.',
          key: const Key('noResults'),
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      );
    }
    return Stack(
      children: [
        ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 16),
          itemCount: _results.length,
          separatorBuilder: (_, _) => const SizedBox(height: 10),
          itemBuilder: (_, i) {
            final milestone = _results[i];
            return _MilestoneTile(
              milestone: milestone,
              selected: _selected?.id == milestone.id,
              onTap: () => _select(milestone),
            );
          },
        ),
        if (_loading)
          const Align(
            alignment: Alignment.topCenter,
            child: LinearProgressIndicator(minHeight: 3),
          ),
      ],
    );
  }

  Widget _statusPanel() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.card,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        boxShadow: AppShadows.card,
      ),
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'How is ${widget.child.name} doing with this?',
            style: AppText.nunito(size: 15, weight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          Text(
            _selected!.description,
            style: Theme.of(context).textTheme.bodySmall,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final status in MilestoneStatus.values)
                _StatusChip(
                  status: status,
                  selected: _status == status,
                  onTap: () => setState(() {
                    _status = status;
                    _submitError = null;
                  }),
                ),
            ],
          ),
          if (_submitError != null) ...[
            const SizedBox(height: 12),
            MessageBanner.error(
              {
                _submitError!.message,
                for (final errors in _submitError!.fieldErrors.values)
                  ...errors,
              }.join(' '),
              key: const Key('recordError'),
            ),
          ],
          const SizedBox(height: 14),
          PrimaryButton(
            key: const Key('saveMilestoneButton'),
            label: 'Save milestone',
            icon: Icons.check_rounded,
            loading: _submitting,
            onPressed: _status == null ? null : _submit,
          ),
        ],
      ),
    );
  }
}

class _MilestoneTile extends StatelessWidget {
  const _MilestoneTile({
    required this.milestone,
    required this.selected,
    required this.onTap,
  });

  final ReferenceMilestone milestone;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      key: Key('milestone_${milestone.key}'),
      onTap: onTap,
      borderColor: selected ? AppColors.tealDeep : null,
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  milestone.description,
                  style: AppText.nunito(size: 15, weight: FontWeight.w700),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 6,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    DomainChip(milestone.domain),
                    Text(
                      milestone.expectedLabel,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Icon(
            selected
                ? Icons.check_circle_rounded
                : Icons.radio_button_unchecked_rounded,
            color: selected ? AppColors.tealDeep : AppColors.mint,
            size: 26,
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.status,
    required this.selected,
    required this.onTap,
  });

  final MilestoneStatus status;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final (color, background, onColor, icon) = switch (status) {
      MilestoneStatus.achieved => (
        AppColors.tealDeep,
        AppColors.mint,
        Colors.white,
        Icons.check_circle_rounded,
      ),
      MilestoneStatus.emerging => (
        AppColors.gold,
        AppColors.goldSoft,
        AppColors.ink,
        Icons.trending_up_rounded,
      ),
      MilestoneStatus.notYet => (
        AppColors.coral,
        AppColors.coralSoft,
        Colors.white,
        Icons.hourglass_bottom_rounded,
      ),
    };
    return PillChip(
      key: Key('status_${status.apiValue}'),
      label: status.label,
      icon: icon,
      color: color,
      background: background,
      selectedForeground: onColor,
      selected: selected,
      onTap: onTap,
    );
  }
}

class _Confirmation extends StatelessWidget {
  const _Confirmation({
    required this.child,
    required this.recorded,
    required this.onRecordAnother,
  });

  final ChildProfile child;
  final RecordedMilestone recorded;
  final VoidCallback onRecordAnother;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: AppCard(
        key: const Key('milestoneRecorded'),
        padding: const EdgeInsets.all(22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              width: 72,
              height: 72,
              alignment: Alignment.center,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.mint,
              ),
              child: const Icon(
                Icons.check_rounded,
                color: AppColors.tealDeep,
                size: 44,
              ),
            ),
            const SizedBox(height: 14),
            Text(
              'Milestone recorded',
              textAlign: TextAlign.center,
              style: AppText.quicksand(size: 24),
            ),
            const SizedBox(height: 8),
            Text(
              '“${recorded.description}” — ${recorded.status.label}',
              textAlign: TextAlign.center,
              style: AppText.nunito(size: 15, weight: FontWeight.w700),
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppColors.goldSoft,
                borderRadius: BorderRadius.circular(AppRadii.field),
              ),
              child: Row(
                children: [
                  const Icon(Icons.auto_graph_rounded, color: AppColors.ink),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      "${child.name}'s developmental profile was updated.",
                      key: const Key('profileUpdated'),
                      style: AppText.nunito(size: 14, weight: FontWeight.w700),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            PrimaryButton(
              key: const Key('recordAnotherButton'),
              label: 'Record another',
              icon: Icons.add_rounded,
              onPressed: onRecordAnother,
            ),
            const SizedBox(height: 10),
            SecondaryButton(
              key: const Key('doneButton'),
              label: 'Done',
              onPressed: () => Navigator.of(context).pop(),
            ),
          ],
        ),
      ),
    );
  }
}
