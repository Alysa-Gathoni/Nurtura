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
import 'rating_stars.dart';

/// Longest note the server accepts (FeedbackManager).
const maxFeedbackComment = 1000;

/// Why the feedback sheet was opened: it changes the heading, and whether the
/// skills seen are asked about.
enum FeedbackSheetMode {
  /// Just marked done.
  done,

  /// Just marked as started but not finished.
  started,

  /// Changing feedback already given.
  edit,
}

/// The one place a caregiver says how an activity went (#185, #283).
///
/// Opened after Done or Started, from "Add feedback", and from Edit. Asks, in
/// this order: how it went; what got in the way (unless it went well); how
/// interested the child was; which skills the caregiver saw (new feedback
/// only; ticked ones are recorded as milestones by the server); an optional
/// rating and note. Closes with the saved feedback, or null when skipped; a
/// 401 ends the session, as elsewhere.
class FeedbackSheet extends StatefulWidget {
  const FeedbackSheet({
    super.key,
    required this.recommendation,
    required this.childName,
    required this.service,
    required this.mode,
  });

  final Recommendation recommendation;
  final String childName;
  final RecommendationService service;
  final FeedbackSheetMode mode;

  /// Opens the sheet; resolves to the saved feedback, or null if skipped.
  static Future<ActivityFeedback?> show(
    BuildContext context, {
    required Recommendation recommendation,
    required String childName,
    required RecommendationService service,
    required FeedbackSheetMode mode,
  }) => showModalBottomSheet<ActivityFeedback>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => FeedbackSheet(
      recommendation: recommendation,
      childName: childName,
      service: service,
      mode: mode,
    ),
  );

  @override
  State<FeedbackSheet> createState() => _FeedbackSheetState();
}

class _FeedbackSheetState extends State<FeedbackSheet> {
  ActivityFeedback? get _saved => widget.recommendation.feedback;
  bool get _editing => widget.mode == FeedbackSheetMode.edit;

  late final _note = TextEditingController(text: _saved?.comment ?? '');
  late FeedbackOutcome? _outcome = _saved?.outcome;
  late final Set<FeedbackIssue> _issues = {...?_saved?.issues};
  late FeedbackInterest? _interest = _saved?.interest;
  late int _rating = _saved?.rating ?? 0;
  final _observed = <String>{};
  List<ObservableSkill> _skills = const [];
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    // Skills seen are recorded as milestones; asked once, with new feedback.
    if (!_editing) _loadSkills();
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
        rating: _rating == 0 ? null : _rating,
        comment: _note.text,
        outcome: _outcome,
        // Nothing "got in the way" of an activity that went well.
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

  /// The heading follows the situation (#283): no trophy for an activity that
  /// didn't work.
  (String, IconData, Color, Color) _heading(NurturaPalette p) {
    if (_editing) {
      return ('Your feedback', Icons.edit_note_rounded, p.cardAlt, p.primary);
    }
    if (_outcome == FeedbackOutcome.didntWork) {
      return (
        'Thanks for trying it',
        Icons.volunteer_activism_rounded,
        p.cardAlt,
        p.primary,
      );
    }
    if (widget.mode == FeedbackSheetMode.started) {
      return ('Good start!', Icons.timelapse_rounded, p.sageSoft, p.sage);
    }
    return ('Well done!', Icons.emoji_events_rounded, p.mustardSoft, p.mustard);
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final name = widget.childName;
    final (title, icon, iconBackground, iconColor) = _heading(p);
    Widget heading(String text, {String? hint}) => Padding(
      padding: const EdgeInsets.only(top: 18, bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(text, style: AppText.nunito(size: 16, weight: FontWeight.w700)),
          if (hint != null) ...[
            const SizedBox(height: 2),
            Text(hint, style: Theme.of(context).textTheme.bodySmall),
          ],
        ],
      ),
    );
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        key: const Key('feedbackSheet'),
        padding: const EdgeInsets.fromLTRB(22, 18, 22, 22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Align(
              alignment: Alignment.topRight,
              child: IconButton(
                key: const Key('closeFeedbackSheet'),
                tooltip: 'Close',
                icon: const Icon(Icons.close_rounded),
                onPressed: _saving ? null : () => Navigator.of(context).pop(),
              ),
            ),
            CircleAvatar(
              radius: 32,
              backgroundColor: iconBackground,
              child: Icon(icon, size: 34, color: iconColor),
            ),
            const SizedBox(height: 12),
            Text(
              title,
              key: const Key('feedbackSheetTitle'),
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
            heading('How did it go?'),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final o in FeedbackOutcome.values)
                  ChoiceChip(
                    key: Key('sheetOutcome_${o.value}'),
                    // A tick widened the chip and moved it to a new line (#293).
                    showCheckmark: false,
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
              heading('What got in the way?', hint: 'Choose any that apply.'),
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
            heading('How interested was $name?'),
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
            if (_skills.isNotEmpty) ...[
              heading(
                'Did you see any of these?',
                hint:
                    'Ticking one adds it to $name\'s milestones as '
                    '“starting”.',
              ),
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
            heading('How helpful was this idea? (optional)'),
            RatingStars(
              rating: _rating,
              onRate: _saving
                  ? null
                  : (value) => setState(() => _rating = value),
            ),
            const SizedBox(height: 10),
            TextField(
              key: const Key('feedbackNote'),
              controller: _note,
              enabled: !_saving,
              minLines: 2,
              maxLines: 4,
              maxLength: maxFeedbackComment,
              textCapitalization: TextCapitalization.sentences,
              decoration: const InputDecoration(
                hintText: 'Anything to add? (optional)',
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 6),
              MessageBanner.error(_error!, key: const Key('feedbackError')),
            ],
            const SizedBox(height: 10),
            PrimaryButton(
              key: const Key('saveFeedbackButton'),
              label: 'Save feedback',
              icon: Icons.check_rounded,
              loading: _saving,
              onPressed: _save,
            ),
            TextButton(
              key: const Key('skipFeedbackButton'),
              onPressed: _saving ? null : () => Navigator.of(context).pop(),
              child: Text(_editing ? 'Cancel' : 'Skip for now'),
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
    return Semantics(
      button: true,
      selected: selected,
      child: InkWell(
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
      ),
    );
  }
}
