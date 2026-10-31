import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/child_profile.dart';
import '../models/recommendation.dart';
import '../services/api_client.dart';
import '../services/recommendation_service.dart';
import '../state/auth_state.dart';
import '../state/engagement.dart';
import '../state/recommendation_cache.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/domain_style.dart';
import '../utils/dates.dart';
import '../widgets/app_card.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';
import '../widgets/nurtura_app_bar.dart';
import '../widgets/pill_chip.dart';
import 'activity_detail_screen.dart';

/// The selected child's recommended activities.
///
/// On open it reads the newest stored batch; if there isn't one, it asks the
/// server to prepare one (which can take ~16 s the first time). Scores and
/// rank numbers are never shown: the API doesn't send them.
///
/// Each batch it receives is saved on the device. If the server can't be
/// reached, the saved batch is shown with a "Saved recommendations"
/// notice (NFR-14).
class RecommendationsScreen extends StatefulWidget {
  const RecommendationsScreen({
    super.key,
    required this.child,
    this.refresh = false,
    this.embedded = false,
  });

  final ChildProfile child;

  /// Shown as the home shell's Today tab, without its own app bar.
  final bool embedded;

  /// Ask for a fresh batch straight away (e.g. right after a milestone was
  /// recorded) instead of showing the newest stored one.
  final bool refresh;

  @override
  State<RecommendationsScreen> createState() => _RecommendationsScreenState();
}

enum _Phase { loading, preparing, ready, error }

class _RecommendationsScreenState extends State<RecommendationsScreen> {
  late final RecommendationService _service = RecommendationService(
    context.read<ApiClient>(),
  );
  late final RecommendationCache _cache = context.read<RecommendationCache>();

  _Phase _phase = _Phase.loading;
  RecommendationBatch? _batch;
  String? _error;

  /// When the batch on screen was saved, if it came from the device
  /// because the server couldn't be reached.
  DateTime? _savedAt;

  @override
  void initState() {
    super.initState();
    _load(regenerate: widget.refresh);
  }

  Future<void> _load({bool regenerate = false}) async {
    setState(() {
      _phase = regenerate ? _Phase.preparing : _Phase.loading;
      _error = null;
    });
    try {
      final batch = regenerate
          ? await _service.generate(widget.child.id)
          : await _service.load(
              widget.child.id,
              onGenerating: () {
                if (mounted) setState(() => _phase = _Phase.preparing);
              },
            );
      if (!batch.isEmpty) await _cache.write(widget.child.id, batch);
      if (!mounted) return;
      // Checking today's ideas keeps the day streak going.
      await context.read<EngagementState>().checkIn();
      if (!mounted) return;
      setState(() {
        _batch = batch;
        _savedAt = null;
        _phase = _Phase.ready;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 401) return _sessionEnded();
      // No response at all (offline or timed out): show what was saved.
      final saved = e.statusCode == null
          ? await _cache.read(widget.child.id)
          : null;
      if (!mounted) return;
      if (saved != null) {
        return setState(() {
          _batch = saved.batch;
          _savedAt = saved.savedAt;
          _phase = _Phase.ready;
        });
      }
      setState(() {
        _error = _messageFor(e);
        _phase = _Phase.error;
      });
    }
  }

  /// Done/feedback saved on the detail screen: show it here and keep the
  /// offline copy in step.
  Future<void> _changed(Recommendation updated) async {
    final batch = _batch;
    if (batch == null) return;
    final next = batch.replacing(updated);
    setState(() => _batch = next);
    await _cache.write(widget.child.id, next);
  }

  Future<void> _sessionEnded() async {
    final auth = context.read<AuthState>();
    Navigator.of(context).popUntil((route) => route.isFirst);
    await auth.sessionExpired();
  }

  String _messageFor(ApiException e) => switch (e.statusCode) {
    403 => 'Recommendations are only available on caregiver accounts.',
    404 =>
      "We couldn't find ${widget.child.name}'s profile. It may have been "
          'removed.',
    // Network problems, timeouts and server errors already have plain
    // messages from the API client.
    _ => e.message,
  };

  @override
  Widget build(BuildContext context) {
    final busy = _phase == _Phase.loading || _phase == _Phase.preparing;
    final content = Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 560),
        child: switch (_phase) {
          _Phase.loading => const Center(
            child: CircularProgressIndicator(
              key: Key('recommendationsLoading'),
            ),
          ),
          _Phase.preparing => _preparing(),
          _Phase.error => _errorView(),
          _Phase.ready => _list(),
        },
      ),
    );
    if (widget.embedded) return content;
    return Scaffold(
      appBar: NurturaAppBar(
        title: 'Ideas for ${widget.child.name}',
        actions: [
          IconButton(
            key: const Key('refreshRecommendationsButton'),
            tooltip: 'Refresh',
            icon: const Icon(Icons.refresh_rounded),
            onPressed: busy ? null : () => _load(regenerate: true),
          ),
        ],
      ),
      body: SafeArea(child: content),
    );
  }

  Widget _preparing() {
    return Padding(
      key: const Key('preparingRecommendations'),
      padding: const EdgeInsets.all(28),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 18),
          Text(
            'Gathering ideas…',
            textAlign: TextAlign.center,
            style: AppText.quicksand(size: 20, color: context.palette.primary),
          ),
          const SizedBox(height: 6),
          Text(
            'The first time can take up to 30 seconds.',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Widget _errorView() {
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          MessageBanner.error(_error!, key: const Key('recommendationsError')),
          const SizedBox(height: 14),
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

  Widget _list() {
    final items = _batch!.items;
    final referral = _batch!.referral;
    if (items.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (referral != null) ...[
                ReferralNotice(referral),
                const SizedBox(height: 12),
              ],
              MessageBanner.info(
                'No ideas for ${widget.child.name} yet. Check back soon.',
                key: const Key('noRecommendations'),
              ),
            ],
          ),
        ),
      );
    }
    return ListView.separated(
      key: const Key('recommendationsList'),
      padding: const EdgeInsets.fromLTRB(20, 4, 20, 24),
      itemCount: items.length + 1,
      separatorBuilder: (_, _) => const SizedBox(height: 12),
      itemBuilder: (context, i) {
        if (i == 0) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_savedAt != null) ...[
                MessageBanner.info(
                  "Saved ideas from ${formatDate(_savedAt!)}. You're offline.",
                  key: const Key('savedRecommendationsNotice'),
                ),
                const SizedBox(height: 12),
              ],
              if (referral != null) ...[
                ReferralNotice(referral),
                const SizedBox(height: 12),
              ],
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Tap an idea to see how to play.',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                  if (widget.embedded)
                    IconButton(
                      key: const Key('refreshRecommendationsButton'),
                      tooltip: 'Refresh',
                      icon: Icon(
                        Icons.refresh_rounded,
                        color: context.palette.primary,
                      ),
                      onPressed: () => _load(regenerate: true),
                    ),
                ],
              ),
            ],
          );
        }
        final item = items[i - 1];
        return RecommendationCard(
          recommendation: item,
          onTap: () => Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => ActivityDetailScreen(
                recommendation: item,
                childName: widget.child.name,
                onChanged: _changed,
              ),
            ),
          ),
        );
      },
    );
  }
}

/// One suggested activity: name, area, age range, a short description and,
/// when there is one, why it was suggested.
class RecommendationCard extends StatelessWidget {
  const RecommendationCard({
    super.key,
    required this.recommendation,
    this.onTap,
  });

  final Recommendation recommendation;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final r = recommendation;
    final style = DomainStyle.of(r.domain, context.palette);
    return AppCard(
      key: Key('recommendation_${r.activityId}'),
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              // A small area tile in the activity's colour.
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: style.background,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(style.icon, color: style.color, size: 24),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(r.activityName, style: AppText.quicksand(size: 18)),
              ),
              if (onTap != null)
                Icon(
                  Icons.chevron_right_rounded,
                  color: context.palette.mutedText,
                ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              DomainChip(r.domain),
              PillChip(
                label: r.ageLabel,
                color: context.palette.mutedText,
                background: context.palette.cardAlt,
                icon: Icons.child_care_rounded,
              ),
              if (r.completion != null)
                PillChip(
                  key: Key('doneChip_${r.activityId}'),
                  label: r.completion!.label,
                  color: context.palette.sage,
                  background: context.palette.sageSoft,
                  icon: r.completion!.partial
                      ? Icons.timelapse_rounded
                      : Icons.check_circle_rounded,
                ),
              if (r.feedback != null)
                PillChip(
                  key: Key('ratingChip_${r.activityId}'),
                  label: '${r.feedback!.rating}/5',
                  color: context.palette.ink,
                  background: context.palette.mustardSoft,
                  icon: Icons.star_rounded,
                ),
            ],
          ),
          if (r.shortDescription.isNotEmpty) ...[
            const SizedBox(height: 10),
            Text(r.shortDescription, style: AppText.nunito(size: 15)),
          ],
          if (r.hasExplanation) ...[
            const SizedBox(height: 12),
            ExplanationBox(r.explanation),
          ],
        ],
      ),
    );
  }
}

/// The clinic-visit suggestion (#161): calm sage colours, not a warning,
/// with the milestones it is about.
class ReferralNotice extends StatelessWidget {
  const ReferralNotice(this.referral, {super.key});

  final Referral referral;

  @override
  Widget build(BuildContext context) {
    final palette = context.palette;
    return Container(
      key: const Key('referralNotice'),
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: palette.sageSoft,
        borderRadius: BorderRadius.circular(AppRadii.field),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.favorite_rounded, size: 20, color: palette.sage),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Worth mentioning at your next clinic visit',
                  style: AppText.nunito(size: 14, weight: FontWeight.w800),
                ),
                const SizedBox(height: 4),
                Text(referral.message, style: AppText.nunito(size: 14)),
                if (referral.milestones.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  for (final m in referral.milestones)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(
                        '•  $m',
                        style: AppText.nunito(
                          size: 14,
                          weight: FontWeight.w700,
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

/// Why an activity was suggested, in the soft-gold explanation style.
class ExplanationBox extends StatelessWidget {
  const ExplanationBox(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('explanationBox'),
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: context.palette.mustardSoft,
        borderRadius: BorderRadius.circular(AppRadii.field),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.lightbulb_rounded,
            size: 20,
            color: context.palette.mustard,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Why this?',
                  style: AppText.nunito(size: 13, weight: FontWeight.w800),
                ),
                const SizedBox(height: 2),
                Text(text, style: AppText.nunito(size: 14)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
