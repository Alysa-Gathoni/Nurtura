import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/recommendation.dart';
import '../services/api_client.dart';
import '../services/recommendation_service.dart';
import '../state/auth_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import 'buttons.dart';
import 'message_banner.dart';

/// The "Well done!" sheet shown after an activity is marked done (#185).
///
/// Asks how interested the child was, how it went and what got in the way
/// (#175), which skills the caregiver saw, and for a note. Ticked skills are
/// recorded as milestones by the server. Closes with the saved feedback, or
/// null when skipped; a 401 ends the session, as elsewhere.
class WellDoneSheet extends StatefulWidget {
  const WellDoneSheet({
    super.key,
    required this.recommendation,
    required this.childName,
    required this.service,
  });

  final Recommendation recommendation;
  final String childName;
  final RecommendationService service;

  /// Opens the sheet; resolves to the saved feedback, or null if skipped.
  static Future<ActivityFeedback?> show(
    BuildContext context, {
    required Recommendation recommendation,
    required String childName,
    required RecommendationService service,
  }) => showModalBottomSheet<ActivityFeedback>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => WellDoneSheet(
      recommendation: recommendation,
      childName: childName,
      service: service,
    ),
  );

  @override
  State<WellDoneSheet> createState() => _WellDoneSheetState();
}

class _WellDoneSheetState extends State<WellDoneSheet> {
  late final _note = TextEditingController(
    text: widget.recommendation.feedback?.comment ?? '',
  );
  late FeedbackInterest? _interest = widget.recommendation.feedback?.interest;
  late FeedbackOutcome? _outcome = widget.recommendation.feedback?.outcome;
  late final Set<FeedbackIssue> _issues = {
    ...?widget.recommendation.feedback?.issues,
  };
  final _observed = <String>{};
  List<ObservableSkill> _skills = const [];
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadSkills();
  }

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  /// Skills are a bonus: if they can't be loaded, the section is hidden.
  Future<void> _loadSkills() async {
    try {
      final skills = await widget.service.observableSkills(
        widget.recommendation.id,
      );
      if (mounted) setState(() => _skills = skills);
    } on ApiException {
      // Leave the list empty.
    }
  }

  Future<void> _save() async {
    if (_outcome == null) {
      setState(() => _error = 'Choose how it went.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final feedback = await widget.service.sendFeedback(
        widget.recommendation.id,
        rating: widget.recommendation.feedback?.rating,
        comment: _note.text,
        outcome: _outcome,
        issues: _outcome == FeedbackOutcome.wentWell
            ? const []
            : FeedbackIssue.values.where(_issues.contains).toList(),
        interest: _interest,
        observed: [
          for (final s in _skills)
            if (_observed.contains(s.key)) s.key,
        ],
      );
      if (mounted) Navigator.of(context).pop(feedback);
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 401) {
        final auth = context.read<AuthState>();
        Navigator.of(context).popUntil((route) => route.isFirst);
        await auth.sessionExpired();
        return;
      }
      setState(() {
        _saving = false;
        _error = e.statusCode == null
            ? "You're offline, so this wasn't saved. Try again when you're "
                  'connected.'
            : e.message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final name = widget.childName;
    Widget heading(String text) => Padding(
      padding: const EdgeInsets.only(top: 18, bottom: 8),
      child: Text(
        text,
        style: AppText.nunito(size: 16, weight: FontWeight.w700),
      ),
    );
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        key: const Key('wellDoneSheet'),
        padding: const EdgeInsets.fromLTRB(22, 18, 22, 22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Align(
              alignment: Alignment.topRight,
              child: IconButton(
                key: const Key('closeWellDone'),
                tooltip: 'Close',
                icon: const Icon(Icons.close_rounded),
                onPressed: _saving ? null : () => Navigator.of(context).pop(),
              ),
            ),
            CircleAvatar(
              radius: 32,
              backgroundColor: p.mustardSoft,
              child: Icon(
                Icons.emoji_events_rounded,
                size: 34,
                color: p.mustard,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Well done!',
              textAlign: TextAlign.center,
              style: AppText.quicksand(size: 26),
            ),
            const SizedBox(height: 4),
            Text(
              'How did “${widget.recommendation.activityName}” go with '
              '$name?',
              textAlign: TextAlign.center,
              style: AppText.nunito(size: 15, color: p.mutedText),
            ),
            heading("$name's interest"),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                for (final i in FeedbackInterest.values)
                  _InterestButton(
                    interest: i,
                    selected: _interest == i,
                    onTap: _saving ? null : () => setState(() => _interest = i),
                  ),
              ],
            ),
            heading('How did it go?'),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final o in FeedbackOutcome.values)
                  ChoiceChip(
                    key: Key('sheetOutcome_${o.value}'),
                    label: Text(o.label),
                    selected: _outcome == o,
                    onSelected: _saving
                        ? null
                        : (_) => setState(() {
                            _outcome = o;
                            _error = null;
                          }),
                  ),
              ],
            ),
            if (_outcome != null && _outcome != FeedbackOutcome.wentWell) ...[
              heading('What got in the way?'),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final i in FeedbackIssue.values)
                    FilterChip(
                      key: Key('sheetIssue_${i.value}'),
                      label: Text(i.label),
                      selected: _issues.contains(i),
                      onSelected: _saving
                          ? null
                          : (on) => setState(
                              () => on ? _issues.add(i) : _issues.remove(i),
                            ),
                    ),
                ],
              ),
            ],
            if (_skills.isNotEmpty) ...[
              heading('Did you see any of these?'),
              Text(
                'Ticking one adds it to $name\'s milestones as “starting”.',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final s in _skills)
                    FilterChip(
                      key: Key('skill_${s.key}'),
                      // Long names wrap instead of being clipped (#214).
                      label: Text(
                        s.description,
                        softWrap: true,
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                      ),
                      selected: _observed.contains(s.key),
                      onSelected: _saving
                          ? null
                          : (on) => setState(
                              () => on
                                  ? _observed.add(s.key)
                                  : _observed.remove(s.key),
                            ),
                    ),
                ],
              ),
            ],
            heading('Notes'),
            TextField(
              key: const Key('wellDoneNote'),
              controller: _note,
              enabled: !_saving,
              minLines: 2,
              maxLines: 4,
              maxLength: 1000,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                hintText: 'Was it too hard? Too easy? Anything else?',
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 6),
              MessageBanner.error(_error!, key: const Key('wellDoneError')),
            ],
            const SizedBox(height: 10),
            PrimaryButton(
              key: const Key('saveProgressButton'),
              label: 'Save progress',
              icon: Icons.check_rounded,
              loading: _saving,
              onPressed: _save,
            ),
            TextButton(
              key: const Key('skipWellDone'),
              onPressed: _saving ? null : () => Navigator.of(context).pop(),
              child: const Text('Skip for now'),
            ),
          ],
        ),
      ),
    );
  }
}

class _InterestButton extends StatelessWidget {
  const _InterestButton({
    required this.interest,
    required this.selected,
    required this.onTap,
  });

  final FeedbackInterest interest;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return InkWell(
      key: Key('interest_${interest.value}'),
      borderRadius: BorderRadius.circular(32),
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.all(4),
        child: Column(
          children: [
            CircleAvatar(
              radius: 24,
              backgroundColor: selected ? p.primary : p.cardAlt,
              child: Icon(
                interest.icon,
                size: 28,
                color: selected ? Colors.white : p.mutedText,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              interest.label,
              style: AppText.nunito(
                size: 13,
                weight: selected ? FontWeight.w800 : FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
