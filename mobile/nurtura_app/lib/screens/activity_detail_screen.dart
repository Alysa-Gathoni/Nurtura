import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/recommendation.dart';
import '../services/api_client.dart';
import '../services/recommendation_service.dart';
import '../state/auth_state.dart';
import '../state/engagement.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/domain_style.dart';
import '../utils/dates.dart';
import '../widgets/app_card.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';
import '../widgets/nurtura_app_bar.dart';
import '../widgets/feedback_sheet.dart';
import '../widgets/pill_chip.dart';
import '../widgets/rating_stars.dart';
import 'recommendations_screen.dart';

/// One suggested activity in full: the steps, what's needed, how it fits at
/// home and its source (#138), then "How did it go?": mark it done or started
/// (FR-14), then give feedback (FR-15) in the one feedback sheet (#283).
class ActivityDetailScreen extends StatefulWidget {
  const ActivityDetailScreen({
    super.key,
    required this.recommendation,
    required this.childName,
    this.onChanged,
    this.onNewBatch,
    this.onProfileChanged,
  });

  final Recommendation recommendation;
  final String childName;

  /// Called with the updated recommendation after a change is saved, so
  /// the list (and its offline copy) can show it.
  final ValueChanged<Recommendation>? onChanged;

  /// Called with the new batch when the caregiver picks one of the options
  /// offered after feedback (#177); the screen then closes.
  final ValueChanged<RecommendationBatch>? onNewBatch;

  /// Called when skills ticked in the feedback sheet were recorded as
  /// milestones (#185), so the child's ideas are out of date.
  final VoidCallback? onProfileChanged;

  @override
  State<ActivityDetailScreen> createState() => _ActivityDetailScreenState();
}

class _ActivityDetailScreenState extends State<ActivityDetailScreen> {
  late final RecommendationService _service = RecommendationService(
    context.read<ApiClient>(),
  );
  late Recommendation _r = widget.recommendation;
  List<FeedbackOption> _options = const [];
  String? _choosing; // activity_id being added
  String? _optionsError;
  bool _savingDone = false;
  String? _doneError;

  @override
  void initState() {
    super.initState();
    if (widget.recommendation.feedback?.outcome != null) _loadOptions();
  }

  /// The options for the saved feedback (#177). Quietly empty if they
  /// can't be loaded: they're a suggestion, not something to wait for.
  Future<void> _loadOptions() async {
    try {
      final options = await _service.options(_r.id);
      if (mounted) setState(() => _options = options);
    } on ApiException {
      if (mounted) setState(() => _options = const []);
    }
  }

  Future<void> _choose(FeedbackOption option) async {
    setState(() {
      _choosing = option.activityId;
      _optionsError = null;
    });
    await _attempt(() async {
      final batch = await _service.chooseOption(_r.id, option.activityId);
      if (!mounted) return;
      widget.onNewBatch?.call(batch);
      Navigator.of(context).pop();
    }, (message) => setState(() => _optionsError = message));
    if (mounted) setState(() => _choosing = null);
  }

  void _update(Recommendation updated) {
    setState(() => _r = updated);
    widget.onChanged?.call(updated);
  }

  /// Runs a request; a 401 signs out, anything else becomes a message.
  Future<bool> _attempt(
    Future<void> Function() request,
    void Function(String) onError,
  ) async {
    try {
      await request();
      return true;
    } on ApiException catch (e) {
      if (!mounted) return false;
      if (e.statusCode == 401) {
        final auth = context.read<AuthState>();
        Navigator.of(context).popUntil((route) => route.isFirst);
        await auth.sessionExpired();
        return false;
      }
      onError(
        e.statusCode == null
            ? "You're offline, so this wasn't saved. Try again when "
                  "you're connected."
            : e.message,
      );
      return false;
    }
  }

  Future<void> _markDone({required bool partial}) async {
    setState(() {
      _savingDone = true;
      _doneError = null;
    });
    await _attempt(() async {
      final completion = await _service.markDone(_r.id, partial: partial);
      if (!mounted) return;
      _update(_r.withProgress(completion: () => completion));
      // Doing an activity counts toward the week streak too.
      await context.read<EngagementState>().checkIn();
      if (!mounted) return;
      setState(() => _savingDone = false);
      await _openFeedback(
        partial ? FeedbackSheetMode.started : FeedbackSheetMode.done,
      );
    }, (message) => setState(() => _doneError = message));
    if (mounted) setState(() => _savingDone = false);
  }

  /// The feedback sheet (#283): after Done or Started, from "Add feedback",
  /// and from Edit. Saving shows the summary, its options and any milestones
  /// recorded.
  Future<void> _openFeedback(FeedbackSheetMode mode) async {
    final saved = await FeedbackSheet.show(
      context,
      recommendation: _r,
      childName: widget.childName,
      service: _service,
      mode: mode,
    );
    if (!mounted || saved == null) return;
    _update(_r.withProgress(feedback: saved));
    if (saved.recorded.isNotEmpty) {
      widget.onProfileChanged?.call();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          key: const Key('milestonesRecordedSnack'),
          content: Text(
            "Added to ${widget.childName}'s milestones: "
            '${saved.recorded.join('; ')}.',
          ),
        ),
      );
    }
    await _loadOptions();
  }

  Future<void> _undoDone() async {
    setState(() {
      _savingDone = true;
      _doneError = null;
    });
    await _attempt(() async {
      await _service.undoDone(_r.id);
      if (mounted) _update(_r.withProgress(completion: () => null));
    }, (message) => setState(() => _doneError = message));
    if (mounted) setState(() => _savingDone = false);
  }

  @override
  Widget build(BuildContext context) {
    final r = _r;
    return Scaffold(
      appBar: const NurturaAppBar(title: 'Activity'),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 560),
            child: ListView(
              key: const Key('activityDetail'),
              padding: const EdgeInsets.all(20),
              children: [
                Text(r.activityName, style: AppText.quicksand(size: 24)),
                const SizedBox(height: 10),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    DomainChip(r.domain),
                    PillChip(
                      label: r.ageLabel,
                      color: context.palette.mutedText,
                      background: context.palette.card,
                      icon: Icons.child_care_rounded,
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                if (r.howToPlay.isNotEmpty)
                  _DetailCard(
                    key: const Key('howToPlay'),
                    icon: Icons.format_list_bulleted_rounded,
                    title: 'How to play',
                    body: r.howToPlay,
                    large: true,
                  ),
                if (r.description.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _DetailCard(
                    key: const Key('materials'),
                    icon: Icons.shopping_basket_outlined,
                    title: "What you'll need",
                    body:
                        r.materialsNeeded ??
                        'Nothing special: just you and ${widget.childName}.',
                  ),
                ],
                if (r.culturalRelevance.trim().isNotEmpty) ...[
                  const SizedBox(height: 12),
                  _DetailCard(
                    key: const Key('atHome'),
                    icon: Icons.home_outlined,
                    title: 'Making it work at home',
                    body: r.culturalRelevance.trim(),
                  ),
                ],
                if (r.hasExplanation) ...[
                  const SizedBox(height: 14),
                  ExplanationBox(r.explanation),
                ],
                const SizedBox(height: 16),
                Text(
                  'Picked for ${widget.childName} on '
                  '${formatDate(r.generatedAt.toLocal())}.',
                  key: const Key('suggestedOn'),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                if (r.source.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    r.sourceSite == null
                        ? 'Based on guidance from ${r.source}.'
                        : 'Based on guidance from ${r.source} '
                              '(${r.sourceSite}).',
                    key: const Key('activitySource'),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
                const SizedBox(height: 24),
                Text('How did it go?', style: AppText.quicksand(size: 20)),
                const SizedBox(height: 10),
                _doneCard(context),
                if (_r.completion != null || _r.feedback != null) ...[
                  const SizedBox(height: 14),
                  _feedbackCard(context),
                ],
                if (_options.isNotEmpty) ...[
                  const SizedBox(height: 18),
                  _optionsSection(context),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _doneCard(BuildContext context) {
    final p = context.palette;
    final done = _r.completion;
    return AppCard(
      key: const Key('doneCard'),
      padding: const EdgeInsets.all(16),
      color: done == null ? null : p.sageSoft,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (done == null) ...[
            Text(
              'Tried it with ${widget.childName}?',
              style: AppText.nunito(size: 16, weight: FontWeight.w700),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: PrimaryButton(
                    key: const Key('markDoneButton'),
                    label: 'Done!',
                    icon: Icons.check_circle_rounded,
                    loading: _savingDone,
                    onPressed: () => _markDone(partial: false),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: SecondaryButton(
                    key: const Key('markStartedButton'),
                    label: 'Started',
                    icon: Icons.timelapse_rounded,
                    onPressed: _savingDone
                        ? null
                        : () => _markDone(partial: true),
                  ),
                ),
              ],
            ),
          ] else ...[
            Row(
              children: [
                Icon(
                  done.partial
                      ? Icons.timelapse_rounded
                      : Icons.check_circle_rounded,
                  color: p.sage,
                  size: 30,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    '${done.label} on ${formatDate(done.date)}',
                    key: const Key('doneStatus'),
                    style: AppText.nunito(
                      size: 16,
                      weight: FontWeight.w800,
                      color: p.sage,
                    ),
                  ),
                ),
                TextButton(
                  key: const Key('undoDoneButton'),
                  onPressed: _savingDone ? null : _undoDone,
                  child: const Text('Undo'),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              done.partial
                  ? 'It may come back so you can finish it.'
                  : "It won't come up again; a new idea takes its place.",
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
          if (_doneError != null) ...[
            const SizedBox(height: 10),
            MessageBanner.error(_doneError!, key: const Key('doneError')),
          ],
        ],
      ),
    );
  }

  /// After the activity is tried: "Add feedback", or the saved feedback with
  /// Edit. Both open the feedback sheet (#283).
  Widget _feedbackCard(BuildContext context) {
    final p = context.palette;
    final saved = _r.feedback;
    if (saved == null) {
      return AppCard(
        key: const Key('feedbackCard'),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Tell us how it went',
              style: AppText.nunito(size: 16, weight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(
              'It helps us suggest better ideas for ${widget.childName}.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            SecondaryButton(
              key: const Key('addFeedbackButton'),
              label: 'Add feedback',
              icon: Icons.rate_review_outlined,
              onPressed: () => _openFeedback(
                _r.completion?.partial == true
                    ? FeedbackSheetMode.started
                    : FeedbackSheetMode.done,
              ),
            ),
          ],
        ),
      );
    }
    return AppCard(
      key: const Key('feedbackCard'),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Thanks for your feedback!',
                  style: AppText.nunito(size: 16, weight: FontWeight.w700),
                ),
              ),
              TextButton(
                key: const Key('editFeedbackButton'),
                onPressed: () => _openFeedback(FeedbackSheetMode.edit),
                child: const Text('Edit'),
              ),
            ],
          ),
          if (saved.outcome != null) ...[
            Text(
              saved.outcome!.label,
              key: const Key('savedOutcome'),
              style: AppText.nunito(size: 15, weight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
          ],
          if (saved.issues.isNotEmpty) ...[
            Text(
              saved.issues.map((i) => i.label).join(' · '),
              key: const Key('savedIssues'),
              style: AppText.nunito(size: 14, color: p.mutedText),
            ),
            const SizedBox(height: 4),
          ],
          if (saved.interest != null) ...[
            Text(
              'Interest: ${saved.interest!.label}',
              key: const Key('savedInterest'),
              style: AppText.nunito(size: 14, color: p.mutedText),
            ),
            const SizedBox(height: 4),
          ],
          if (saved.rating != null)
            RatingStars(rating: saved.rating!, keyPrefix: 'savedStar'),
          if (saved.comment.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              '“${saved.comment}”',
              key: const Key('savedComment'),
              style: AppText.nunito(size: 15, height: 1.4),
            ),
          ],
        ],
      ),
    );
  }

  /// "What next?": the options offered after feedback (#177).
  Widget _optionsSection(BuildContext context) {
    final p = context.palette;
    return Column(
      key: const Key('feedbackOptions'),
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('What next?', style: AppText.quicksand(size: 20)),
        const SizedBox(height: 4),
        Text(
          'Ideas based on how it went.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        if (_optionsError != null) ...[
          const SizedBox(height: 8),
          MessageBanner.error(_optionsError!, key: const Key('optionsError')),
        ],
        for (final o in _options) ...[
          const SizedBox(height: 10),
          AppCard(
            key: Key('option_${o.activityId}'),
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  o.title,
                  style: AppText.nunito(
                    size: 13,
                    weight: FontWeight.w800,
                    color: p.primary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(o.activityName, style: AppText.quicksand(size: 18)),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    DomainChip(o.domain),
                    PillChip(
                      label: o.ageLabel,
                      color: p.mutedText,
                      background: p.cardAlt,
                      icon: Icons.child_care_rounded,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(o.why, style: AppText.nunito(size: 14)),
                if (o.shortDescription.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    o.shortDescription,
                    style: AppText.nunito(size: 14, color: p.mutedText),
                  ),
                ],
                if (o.tip.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  MessageBanner.info(
                    o.tip,
                    key: Key('optionTip_${o.activityId}'),
                  ),
                ],
                const SizedBox(height: 10),
                SecondaryButton(
                  key: Key('chooseOption_${o.activityId}'),
                  label: _choosing == o.activityId
                      ? 'Adding…'
                      : 'Try this instead',
                  icon: Icons.add_rounded,
                  onPressed: _choosing != null ? null : () => _choose(o),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

/// A titled block of the activity: the steps, the materials, the home note.
class _DetailCard extends StatelessWidget {
  const _DetailCard({
    super.key,
    required this.icon,
    required this.title,
    required this.body,
    this.large = false,
  });

  final IconData icon;
  final String title;
  final String body;
  final bool large;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return AppCard(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 18, color: p.primary),
              const SizedBox(width: 8),
              Text(
                title,
                style: AppText.nunito(
                  size: 13,
                  weight: FontWeight.w800,
                  color: p.mutedText,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(body, style: AppText.nunito(size: large ? 16 : 15, height: 1.4)),
        ],
      ),
    );
  }
}
