import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/admin.dart';
import '../../services/admin_service.dart';
import '../../services/api_client.dart';
import '../../state/auth_state.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_theme.dart';
import '../../theme/domain_style.dart';
import '../../utils/dates.dart';
import '../../widgets/app_card.dart';
import '../../widgets/buttons.dart';
import '../../widgets/message_banner.dart';
import '../../widgets/pill_chip.dart';
import 'admin_activity_form_screen.dart';

/// Caregivers' ratings and comments against each activity (#123, FR-16).
/// No child or caregiver details.
class AdminFeedbackScreen extends StatefulWidget {
  const AdminFeedbackScreen({super.key});

  @override
  State<AdminFeedbackScreen> createState() => _AdminFeedbackScreenState();
}

class _AdminFeedbackScreenState extends State<AdminFeedbackScreen> {
  static const _page = 30;

  late final AdminService _service = AdminService(context.read<ApiClient>());
  int? _rating;
  List<AdminFeedback> _items = [];
  int _count = 0;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load({bool more = false}) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final page = await _service.feedback(
        rating: _rating,
        limit: _page,
        offset: more ? _items.length : 0,
      );
      if (!mounted) return;
      setState(() {
        _items = more ? [..._items, ...page.items] : page.items;
        _count = page.count;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 401) {
        return context.read<AuthState>().sessionExpired();
      }
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _openActivity(int id) async {
    try {
      final activity = await _service.activity(id);
      if (!mounted) return;
      await Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => AdminActivityFormScreen(activity: activity),
        ),
      );
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        key: const Key('adminFeedback'),
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 28),
        children: [
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (final r in <int?>[null, 5, 4, 3, 2, 1])
                  Padding(
                    padding: const EdgeInsets.only(right: 6),
                    child: PillChip(
                      key: Key('rating_${r ?? 'all'}'),
                      label: r == null ? 'All' : '$r★',
                      color: p.mustard,
                      background: p.mustardSoft,
                      selectedForeground: p.ink,
                      selected: _rating == r,
                      onTap: () {
                        setState(() => _rating = r);
                        _load();
                      },
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          if (_error != null) ...[
            MessageBanner.error(_error!, key: const Key('feedbackError')),
            const SizedBox(height: 10),
            SecondaryButton(
              label: 'Try again',
              icon: Icons.refresh_rounded,
              onPressed: _load,
            ),
          ] else if (_loading && _items.isEmpty)
            const Padding(
              padding: EdgeInsets.all(32),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (_items.isEmpty)
            Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                'No feedback yet.',
                key: const Key('noFeedback'),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            )
          else ...[
            Text(
              '$_count rating${_count == 1 ? '' : 's'}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            for (final f in _items)
              Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _FeedbackCard(
                  feedback: f,
                  onOpen: () => _openActivity(f.activityId),
                ),
              ),
            if (_items.length < _count)
              SecondaryButton(
                key: const Key('moreFeedback'),
                label: 'Show more',
                onPressed: _loading ? null : () => _load(more: true),
              ),
          ],
        ],
      ),
    );
  }
}

class _FeedbackCard extends StatelessWidget {
  const _FeedbackCard({required this.feedback, required this.onOpen});

  final AdminFeedback feedback;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final f = feedback;
    final p = context.palette;
    final done = switch (f.completion) {
      'completed' => 'Done',
      'partially_completed' => 'Partly done',
      _ => 'Not marked done',
    };
    return AppCard(
      key: Key('feedback_${f.id}'),
      onTap: onOpen,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Text(
                '★' * f.rating + '☆' * (5 - f.rating),
                semanticsLabel: '${f.rating} out of 5',
                style: AppText.nunito(size: 16, color: p.mustard),
              ),
              const Spacer(),
              Text(
                formatDate(f.submitted.toLocal()),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
          if (f.comment.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              '“${f.comment}”',
              style: AppText.nunito(size: 14.5, height: 1.4),
            ),
          ],
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      f.activityName,
                      style: AppText.nunito(size: 14, weight: FontWeight.w800),
                    ),
                    Text(
                      '${f.activityCode} · ${domainLabels[f.domain] ?? f.domain} · $done',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right_rounded, color: p.mutedText),
            ],
          ),
        ],
      ),
    );
  }
}
