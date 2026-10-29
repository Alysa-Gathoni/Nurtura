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
import '../widgets/pill_chip.dart';
import 'recommendations_screen.dart';

/// Longest comment the server accepts (FeedbackManager).
const maxFeedbackComment = 1000;

/// One suggested activity in full: the steps, what's needed, how it fits at
/// home and its source (#138), then "How did it go?": mark it done (FR-14) and leave
/// feedback (FR-15).
class ActivityDetailScreen extends StatefulWidget {
  const ActivityDetailScreen({
    super.key,
    required this.recommendation,
    required this.childName,
    this.onChanged,
  });

  final Recommendation recommendation;
  final String childName;

  /// Called with the updated recommendation after a change is saved, so
  /// the list (and its offline copy) can show it.
  final ValueChanged<Recommendation>? onChanged;

  @override
  State<ActivityDetailScreen> createState() => _ActivityDetailScreenState();
}

class _ActivityDetailScreenState extends State<ActivityDetailScreen> {
  late final RecommendationService _service = RecommendationService(
    context.read<ApiClient>(),
  );
  late Recommendation _r = widget.recommendation;
  late final _comment = TextEditingController(
    text: widget.recommendation.feedback?.comment ?? '',
  );

  late int _rating = widget.recommendation.feedback?.rating ?? 0;
  late bool _editingFeedback = widget.recommendation.feedback == null;
  bool _savingDone = false;
  bool _sendingFeedback = false;
  String? _doneError;
  String? _feedbackError;

  @override
  void dispose() {
    _comment.dispose();
    super.dispose();
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
      // Doing an activity counts toward the day streak too.
      await context.read<EngagementState>().checkIn();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            partial
                ? 'Nice start! Saved as partly done.'
                : 'Well done! Marked as done.',
          ),
        ),
      );
    }, (message) => setState(() => _doneError = message));
    if (mounted) setState(() => _savingDone = false);
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

  Future<void> _sendFeedback() async {
    if (_rating == 0) {
      setState(() => _feedbackError = 'Tap a star to rate the activity.');
      return;
    }
    setState(() {
      _sendingFeedback = true;
      _feedbackError = null;
    });
    await _attempt(() async {
      final feedback = await _service.sendFeedback(
        _r.id,
        rating: _rating,
        comment: _comment.text,
      );
      if (!mounted) return;
      _update(_r.withProgress(feedback: feedback));
      setState(() => _editingFeedback = false);
    }, (message) => setState(() => _feedbackError = message));
    if (mounted) setState(() => _sendingFeedback = false);
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
                const SizedBox(height: 14),
                _feedbackCard(context),
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
                    key: const Key('markPartlyButton'),
                    label: 'Partly',
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
                      : Icons.emoji_events_rounded,
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

  Widget _feedbackCard(BuildContext context) {
    final p = context.palette;
    final saved = _r.feedback;
    if (saved != null && !_editingFeedback) {
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
                  onPressed: () => setState(() => _editingFeedback = true),
                  child: const Text('Edit'),
                ),
              ],
            ),
            _Stars(rating: saved.rating, color: p.mustard),
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
    return AppCard(
      key: const Key('feedbackCard'),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'How helpful was this?',
            style: AppText.nunito(size: 16, weight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          _Stars(
            rating: _rating,
            color: p.mustard,
            onRate: _sendingFeedback
                ? null
                : (value) => setState(() {
                    _rating = value;
                    _feedbackError = null;
                  }),
          ),
          const SizedBox(height: 10),
          TextField(
            key: const Key('feedbackComment'),
            controller: _comment,
            enabled: !_sendingFeedback,
            minLines: 2,
            maxLines: 5,
            maxLength: maxFeedbackComment,
            textCapitalization: TextCapitalization.sentences,
            decoration: const InputDecoration(
              hintText: 'Anything to add? (optional)',
            ),
          ),
          if (_feedbackError != null) ...[
            const SizedBox(height: 6),
            MessageBanner.error(
              _feedbackError!,
              key: const Key('feedbackError'),
            ),
          ],
          const SizedBox(height: 10),
          PrimaryButton(
            key: const Key('sendFeedbackButton'),
            label: saved == null ? 'Send feedback' : 'Update feedback',
            icon: Icons.send_rounded,
            loading: _sendingFeedback,
            onPressed: _sendFeedback,
          ),
        ],
      ),
    );
  }
}

/// Five stars; tappable when [onRate] is set.
class _Stars extends StatelessWidget {
  const _Stars({required this.rating, required this.color, this.onRate});

  final int rating;
  final Color color;
  final ValueChanged<int>? onRate;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        for (var i = 1; i <= 5; i++)
          IconButton(
            key: Key('star_$i'),
            tooltip: '$i out of 5',
            visualDensity: VisualDensity.compact,
            onPressed: onRate == null ? null : () => onRate!(i),
            icon: Icon(
              i <= rating ? Icons.star_rounded : Icons.star_outline_rounded,
              color: i <= rating ? color : context.palette.mutedText,
              size: 32,
            ),
            disabledColor: i <= rating ? color : context.palette.mutedText,
          ),
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
