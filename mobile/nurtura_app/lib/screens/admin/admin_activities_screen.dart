import 'dart:async';

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/admin.dart';
import '../../services/admin_service.dart';
import '../../services/api_client.dart';
import '../../state/auth_state.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_theme.dart';
import '../../theme/domain_style.dart';
import '../../widgets/app_card.dart';
import '../../widgets/buttons.dart';
import '../../widgets/message_banner.dart';
import '../../widgets/pill_chip.dart';
import 'admin_activity_form_screen.dart';

/// The activity library for administrators (#123, FR-13): search, filter by
/// status and area, add, and open one to edit or move through review.
class AdminActivitiesScreen extends StatefulWidget {
  const AdminActivitiesScreen({super.key, this.initialStatus});

  final String? initialStatus;

  @override
  State<AdminActivitiesScreen> createState() => _AdminActivitiesScreenState();
}

class _AdminActivitiesScreenState extends State<AdminActivitiesScreen> {
  static const _statuses = [
    (null, 'All'),
    ('draft', 'Draft'),
    ('under_review', 'Under review'),
    ('published', 'Published'),
  ];

  late final AdminService _service = AdminService(context.read<ApiClient>());
  final _search = TextEditingController();
  Timer? _debounce;
  late String? _status = widget.initialStatus;
  String? _domain;
  List<AdminActivity>? _items;
  String? _error;

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
    setState(() => _error = null);
    try {
      final items = await _service.activities(
        status: _status,
        domain: _domain,
        search: _search.text,
      );
      if (mounted) setState(() => _items = items);
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 401) {
        return context.read<AuthState>().sessionExpired();
      }
      setState(() => _error = e.message);
    }
  }

  void _searchChanged(String _) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), _load);
  }

  Future<void> _open([AdminActivity? activity]) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => AdminActivityFormScreen(activity: activity),
      ),
    );
    if (changed == true) _load();
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final items = _items;
    return Scaffold(
      backgroundColor: Colors.transparent,
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('addActivityButton'),
        onPressed: () => _open(),
        backgroundColor: p.primary,
        foregroundColor: p.onPrimary,
        icon: const Icon(Icons.add_rounded),
        label: const Text('Add activity'),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          key: const Key('adminActivities'),
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 96),
          children: [
            TextField(
              key: const Key('activitySearch'),
              controller: _search,
              onChanged: _searchChanged,
              decoration: const InputDecoration(
                hintText: 'Search by name, ID or description',
                prefixIcon: Icon(Icons.search_rounded),
              ),
            ),
            const SizedBox(height: 10),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final (value, label) in _statuses)
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: PillChip(
                        key: Key('status_${value ?? 'all'}'),
                        label: label,
                        color: p.primary,
                        background: p.primarySoft,
                        selectedForeground: p.onPrimary,
                        selected: _status == value,
                        onTap: () {
                          setState(() => _status = value);
                          _load();
                        },
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final domain in developmentalDomains)
                    Padding(
                      padding: const EdgeInsets.only(right: 6),
                      child: DomainChip(
                        domain,
                        key: Key('area_$domain'),
                        selected: _domain == domain,
                        onTap: () {
                          setState(
                            () => _domain = _domain == domain ? null : domain,
                          );
                          _load();
                        },
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            if (_error != null) ...[
              MessageBanner.error(_error!, key: const Key('activitiesError')),
              const SizedBox(height: 10),
              SecondaryButton(
                label: 'Try again',
                icon: Icons.refresh_rounded,
                onPressed: _load,
              ),
            ] else if (items == null)
              const Padding(
                padding: EdgeInsets.all(32),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (items.isEmpty)
              Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  'No activities match.',
                  key: const Key('noActivities'),
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              )
            else ...[
              Text(
                '${items.length} activit${items.length == 1 ? 'y' : 'ies'}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 8),
              for (final a in items)
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child: _ActivityCard(activity: a, onTap: () => _open(a)),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Colours for an activity's review status.
({Color fg, Color bg}) statusColours(BuildContext context, String status) {
  final p = context.palette;
  return switch (status) {
    'published' => (fg: p.sage, bg: p.sageSoft),
    'under_review' => (fg: p.mustard, bg: p.mustardSoft),
    _ => (fg: p.mutedText, bg: p.cardAlt),
  };
}

class StatusPill extends StatelessWidget {
  const StatusPill({super.key, required this.status, required this.label});

  final String status, label;

  @override
  Widget build(BuildContext context) {
    final c = statusColours(context, status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
      decoration: BoxDecoration(
        color: c.bg,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: AppText.nunito(size: 11.5, weight: FontWeight.w800, color: c.fg),
      ),
    );
  }
}

class _ActivityCard extends StatelessWidget {
  const _ActivityCard({required this.activity, required this.onTap});

  final AdminActivity activity;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final a = activity;
    final p = context.palette;
    return AppCard(
      key: Key('activity_${a.activityId}'),
      onTap: onTap,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(child: Text(a.name, style: AppText.quicksand(size: 16))),
              StatusPill(status: a.status, label: a.statusLabel),
            ],
          ),
          const SizedBox(height: 4),
          Text(
            '${a.activityId} · ${a.ageRange.replaceAll('-', '–')}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Flexible(
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: FittedBox(
                    fit: BoxFit.scaleDown,
                    child: DomainChip(a.domain),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Icon(Icons.auto_awesome_rounded, size: 15, color: p.mutedText),
              Text(
                ' ${a.timesRecommended}',
                style: AppText.nunito(size: 12.5, weight: FontWeight.w700),
              ),
              const SizedBox(width: 10),
              Icon(Icons.star_rounded, size: 16, color: p.mustard),
              Text(
                a.averageRating == null
                    ? ' –'
                    : ' ${a.averageRating} (${a.feedbackCount})',
                style: AppText.nunito(size: 12.5, weight: FontWeight.w700),
              ),
              if (a.status == 'published' && !a.searchable) ...[
                const SizedBox(width: 10),
                Tooltip(
                  message: 'Not searchable yet: update the search index on the dashboard',
                  child: Icon(
                    Icons.search_off_rounded,
                    size: 17,
                    color: p.rose,
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
