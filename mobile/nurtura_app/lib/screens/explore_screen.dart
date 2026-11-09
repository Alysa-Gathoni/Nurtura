import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/child_profile.dart';
import '../models/explore_activity.dart';
import '../models/recommendation.dart';
import '../services/api_client.dart';
import '../services/explore_service.dart';
import '../state/auth_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/domain_style.dart';
import '../widgets/app_card.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';
import '../widgets/pill_chip.dart';

/// Explore (#194): browse and search activities for the child, save them
/// for later, or add one to today's ideas.
///
/// Without a search or filter it shows "Based on [child]'s interests",
/// "Saved for later" and every activity for the child's age; a search
/// (by meaning, on the server) or a filter shows one list of results.
class ExploreScreen extends StatefulWidget {
  const ExploreScreen({super.key, required this.child, this.onTried});

  final ChildProfile child;

  /// Called with the new batch when an activity is added to the ideas.
  final ValueChanged<RecommendationBatch>? onTried;

  @override
  State<ExploreScreen> createState() => _ExploreScreenState();
}

class _ExploreScreenState extends State<ExploreScreen> {
  late final ExploreService _service = ExploreService(
    context.read<ApiClient>(),
  );
  final _search = TextEditingController();
  Timer? _debounce;

  String? _area;
  bool _noMaterials = false;
  bool _quick = false;
  bool _savedOnly = false;

  List<ExploreActivity>? _results;
  List<ExploreActivity> _forInterests = const [];
  List<ExploreActivity> _saved = const [];
  String? _error;
  int _request = 0;

  bool get _filtered =>
      _search.text.trim().isNotEmpty ||
      _area != null ||
      _noMaterials ||
      _quick ||
      _savedOnly;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final request = ++_request;
    setState(() => _error = null);
    final id = widget.child.id;
    try {
      final results = await _service.list(
        id,
        query: _search.text,
        area: _area,
        noMaterials: _noMaterials,
        quick: _quick,
        savedOnly: _savedOnly,
      );
      var forInterests = _forInterests;
      var saved = _saved;
      if (!_filtered) {
        forInterests = widget.child.interests.isEmpty
            ? const []
            : await _service.list(id, forInterests: true, limit: 8);
        saved = await _service.list(id, savedOnly: true, limit: 8);
      }
      if (!mounted || request != _request) return; // a newer search won
      setState(() {
        _results = results;
        _forInterests = forInterests;
        _saved = saved;
      });
    } on ApiException catch (e) {
      if (!mounted || request != _request) return;
      if (e.statusCode == 401) return _sessionEnded();
      setState(() => _error = e.message);
    }
  }

  void _searchChanged(String _) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), _load);
  }

  Future<void> _sessionEnded() async {
    final auth = context.read<AuthState>();
    Navigator.of(context).popUntil((route) => route.isFirst);
    await auth.sessionExpired();
  }

  void _replace(ExploreActivity updated) {
    List<ExploreActivity> swap(List<ExploreActivity> list) => [
      for (final a in list) a.activityId == updated.activityId ? updated : a,
    ];
    setState(() {
      _results = _results == null ? null : swap(_results!);
      _forInterests = swap(_forInterests);
      _saved = updated.saved
          ? [
              updated,
              ..._saved.where((a) => a.activityId != updated.activityId),
            ]
          : _saved.where((a) => a.activityId != updated.activityId).toList();
    });
  }

  Future<ExploreActivity?> _toggleSaved(ExploreActivity a) async {
    final updated = a.withSaved(!a.saved);
    _replace(updated); // shown at once; put back if the server refuses
    try {
      if (updated.saved) {
        await _service.save(widget.child.id, a.activityId);
      } else {
        await _service.unsave(widget.child.id, a.activityId);
      }
      return updated;
    } on ApiException catch (e) {
      if (!mounted) return null;
      _replace(a);
      if (e.statusCode == 401) {
        await _sessionEnded();
        return null;
      }
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
      return null;
    }
  }

  Future<void> _open(ExploreActivity activity) async {
    final tried = await showModalBottomSheet<RecommendationBatch>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => _ActivitySheet(
        activity: activity,
        childName: widget.child.name,
        onToggleSaved: _toggleSaved,
        onTry: () => _service.tryActivity(widget.child.id, activity.activityId),
      ),
    );
    if (tried == null || !mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        key: const Key('exploreTried'),
        content: Text("Added to ${widget.child.name}'s ideas for today."),
      ),
    );
    widget.onTried?.call(tried);
  }

  @override
  Widget build(BuildContext context) {
    final name = widget.child.name;
    final results = _results;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        key: const Key('exploreList'),
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 28),
        children: [
          TextField(
            key: const Key('exploreSearch'),
            controller: _search,
            onChanged: _searchChanged,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _load(),
            decoration: InputDecoration(
              prefixIcon: const Icon(Icons.search_rounded),
              hintText: 'Search, e.g. "messy play with water"',
              suffixIcon: _search.text.isEmpty
                  ? null
                  : IconButton(
                      tooltip: 'Clear',
                      icon: const Icon(Icons.close_rounded),
                      onPressed: () {
                        _search.clear();
                        _load();
                      },
                    ),
            ),
          ),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (final d in developmentalDomains)
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: ChoiceChip(
                      key: Key('exploreArea_$d'),
                      label: Text(domainLabels[d] ?? d),
                      selected: _area == d,
                      onSelected: (on) {
                        setState(() => _area = on ? d : null);
                        _load();
                      },
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            children: [
              FilterChip(
                key: const Key('exploreNoMaterials'),
                label: const Text('No materials'),
                selected: _noMaterials,
                onSelected: (on) {
                  setState(() => _noMaterials = on);
                  _load();
                },
              ),
              FilterChip(
                key: const Key('exploreQuick'),
                label: const Text('Quick'),
                selected: _quick,
                onSelected: (on) {
                  setState(() => _quick = on);
                  _load();
                },
              ),
              FilterChip(
                key: const Key('exploreSaved'),
                avatar: const Icon(Icons.bookmark_rounded, size: 18),
                label: const Text('Saved'),
                selected: _savedOnly,
                onSelected: (on) {
                  setState(() => _savedOnly = on);
                  _load();
                },
              ),
            ],
          ),
          const SizedBox(height: 14),
          if (_error != null) ...[
            MessageBanner.error(_error!, key: const Key('exploreError')),
            const SizedBox(height: 10),
            SecondaryButton(
              label: 'Try again',
              icon: Icons.refresh_rounded,
              onPressed: _load,
            ),
          ] else if (results == null)
            const Padding(
              padding: EdgeInsets.all(30),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_filtered) ...[
            _Heading(
              results.isEmpty ? 'Nothing found' : 'Results',
              results.isEmpty
                  ? 'Try other words or fewer filters.'
                  : 'Best matches first',
            ),
            for (final a in results) _card(a),
          ] else ...[
            if (_forInterests.isNotEmpty) ...[
              _Heading(
                "Based on $name's interests",
                widget.child.interests.join(', '),
              ),
              SizedBox(
                height: 210,
                child: ListView(
                  key: const Key('exploreInterests'),
                  scrollDirection: Axis.horizontal,
                  children: [
                    for (final a in _forInterests)
                      SizedBox(width: 250, child: _card(a, compact: true)),
                  ],
                ),
              ),
              const SizedBox(height: 14),
            ],
            if (_saved.isNotEmpty) ...[
              const _Heading('Saved for later', 'Tap one to try it'),
              for (final a in _saved) _card(a),
              const SizedBox(height: 14),
            ],
            _Heading('All ideas for $name', 'Suited to their age'),
            for (final a in results) _card(a),
          ],
        ],
      ),
    );
  }

  Widget _card(ExploreActivity a, {bool compact = false}) => Padding(
    padding: EdgeInsets.only(bottom: 10, right: compact ? 10 : 0),
    child: _ActivityCard(
      activity: a,
      compact: compact,
      onTap: () => _open(a),
      onToggleSaved: () => _toggleSaved(a),
    ),
  );
}

class _Heading extends StatelessWidget {
  const _Heading(this.title, this.subtitle);

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 10),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: AppText.quicksand(size: 19)),
        if (subtitle.isNotEmpty)
          Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
      ],
    ),
  );
}

class _ActivityCard extends StatelessWidget {
  const _ActivityCard({
    required this.activity,
    required this.onTap,
    required this.onToggleSaved,
    this.compact = false,
  });

  final ExploreActivity activity;
  final VoidCallback onTap;
  final VoidCallback onToggleSaved;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final a = activity;
    return AppCard(
      key: Key('explore_${a.activityId}'),
      onTap: onTap,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  a.name,
                  maxLines: compact ? 1 : 2,
                  overflow: TextOverflow.ellipsis,
                  style: AppText.quicksand(size: 17),
                ),
              ),
              IconButton(
                key: Key('save_${a.activityId}'),
                tooltip: a.saved ? 'Remove from saved' : 'Save for later',
                icon: Icon(
                  a.saved
                      ? Icons.bookmark_rounded
                      : Icons.bookmark_border_rounded,
                  color: a.saved ? p.primary : p.mutedText,
                ),
                onPressed: onToggleSaved,
              ),
            ],
          ),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              DomainChip(a.domain),
              PillChip(
                label: a.ageLabel,
                color: p.mutedText,
                background: p.cardAlt,
                icon: Icons.child_care_rounded,
              ),
            ],
          ),
          if (a.shortDescription.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              a.shortDescription,
              maxLines: compact ? 2 : 3,
              overflow: TextOverflow.ellipsis,
              style: AppText.nunito(size: 14),
            ),
          ],
        ],
      ),
    );
  }
}

/// The whole activity, with Save and "Try this". Closes with the new batch
/// when the activity was added to the ideas.
class _ActivitySheet extends StatefulWidget {
  const _ActivitySheet({
    required this.activity,
    required this.childName,
    required this.onToggleSaved,
    required this.onTry,
  });

  final ExploreActivity activity;
  final String childName;
  final Future<ExploreActivity?> Function(ExploreActivity) onToggleSaved;
  final Future<RecommendationBatch> Function() onTry;

  @override
  State<_ActivitySheet> createState() => _ActivitySheetState();
}

class _ActivitySheetState extends State<_ActivitySheet> {
  late ExploreActivity _a = widget.activity;
  bool _trying = false;
  String? _error;

  Future<void> _try() async {
    setState(() {
      _trying = true;
      _error = null;
    });
    try {
      final batch = await widget.onTry();
      if (mounted) Navigator.of(context).pop(batch);
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _trying = false;
        _error = e.statusCode == null
            ? "You're offline, so it wasn't added. Try again when you're "
                  'connected.'
            : e.message;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final a = _a;
    Widget section(String title, String text) => Padding(
      padding: const EdgeInsets.only(top: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: AppText.nunito(size: 14, weight: FontWeight.w800)),
          const SizedBox(height: 2),
          Text(text, style: AppText.nunito(size: 15, height: 1.4)),
        ],
      ),
    );
    return SingleChildScrollView(
      key: const Key('exploreSheet'),
      padding: const EdgeInsets.fromLTRB(22, 22, 22, 22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(a.name, style: AppText.quicksand(size: 22)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              DomainChip(a.domain),
              PillChip(
                label: a.ageLabel,
                color: p.mutedText,
                background: p.cardAlt,
                icon: Icons.child_care_rounded,
              ),
            ],
          ),
          section('How to do it', a.description),
          section('You need', a.materialsNeeded ?? 'Nothing special'),
          if (a.culturalRelevance.isNotEmpty)
            section('Make it your own', a.culturalRelevance),
          if (a.source.isNotEmpty)
            section(
              'Source',
              a.sourceUrl.isEmpty ? a.source : '${a.source} · ${a.sourceUrl}',
            ),
          if (_error != null) ...[
            const SizedBox(height: 10),
            MessageBanner.error(_error!, key: const Key('tryError')),
          ],
          const SizedBox(height: 18),
          PrimaryButton(
            key: const Key('tryActivityButton'),
            label: 'Try this with ${widget.childName}',
            icon: Icons.play_arrow_rounded,
            loading: _trying,
            onPressed: _try,
          ),
          const SizedBox(height: 8),
          SecondaryButton(
            key: const Key('sheetSaveButton'),
            label: a.saved ? 'Saved for later' : 'Save for later',
            icon: a.saved
                ? Icons.bookmark_rounded
                : Icons.bookmark_border_rounded,
            onPressed: _trying
                ? null
                : () async {
                    final updated = await widget.onToggleSaved(a);
                    if (updated != null && mounted) {
                      setState(() => _a = updated);
                    }
                  },
          ),
        ],
      ),
    );
  }
}
