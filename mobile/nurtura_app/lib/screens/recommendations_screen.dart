import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/child_profile.dart';
import '../models/recommendation.dart';
import '../services/api_client.dart';
import '../services/recommendation_service.dart';
import '../state/auth_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/domain_style.dart';
import '../widgets/app_card.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';
import '../widgets/nurtura_app_bar.dart';
import '../widgets/pill_chip.dart';

/// The selected child's recommended activities.
///
/// On open it reads the newest stored batch; if there isn't one, it asks the
/// server to prepare one (which can take ~16 s the first time). Scores and
/// rank numbers are never shown: the API doesn't send them.
class RecommendationsScreen extends StatefulWidget {
  const RecommendationsScreen({
    super.key,
    required this.child,
    this.refresh = false,
  });

  final ChildProfile child;

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

  _Phase _phase = _Phase.loading;
  RecommendationBatch? _batch;
  String? _error;

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
      if (!mounted) return;
      setState(() {
        _batch = batch;
        _phase = _Phase.ready;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 401) return _sessionEnded();
      setState(() {
        _error = _messageFor(e);
        _phase = _Phase.error;
      });
    }
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
      body: SafeArea(
        child: Center(
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
        ),
      ),
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
            'Preparing recommendations...',
            textAlign: TextAlign.center,
            style: AppText.quicksand(size: 20, color: AppColors.tealDeep),
          ),
          const SizedBox(height: 6),
          Text(
            'This can take up to half a minute the first time.',
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
    if (items.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: Center(
          child: MessageBanner.info(
            "We don't have activities to suggest for ${widget.child.name} "
            'yet. Please check back later.',
            key: const Key('noRecommendations'),
          ),
        ),
      );
    }
    return ListView.separated(
      key: const Key('recommendationsList'),
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 24),
      itemCount: items.length + 1,
      separatorBuilder: (_, _) => const SizedBox(height: 12),
      itemBuilder: (context, i) {
        if (i == 0) {
          return Text(
            'Activities to try with ${widget.child.name}, chosen from what '
            "you've told us.",
            style: Theme.of(context).textTheme.bodySmall,
          );
        }
        return RecommendationCard(recommendation: items[i - 1]);
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
    return AppCard(
      key: Key('recommendation_${r.activityId}'),
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(r.activityName, style: AppText.quicksand(size: 19)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              DomainChip(r.domain),
              PillChip(
                label: r.ageLabel,
                color: AppColors.mutedText,
                background: AppColors.paper,
                icon: Icons.child_care_rounded,
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
        color: AppColors.goldSoft,
        borderRadius: BorderRadius.circular(AppRadii.field),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.lightbulb_rounded, size: 20, color: AppColors.gold),
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
