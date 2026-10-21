import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../models/admin.dart';
import '../../services/admin_service.dart';
import '../../services/api_client.dart';
import '../../state/auth_state.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_theme.dart';
import '../../widgets/app_card.dart';
import '../../widgets/buttons.dart';
import '../../widgets/message_banner.dart';
import '../../widgets/nurtura_app_bar.dart';
import 'admin_activities_screen.dart';

/// Add an activity, or view and edit one and move it through review
/// (#123, FR-13, DR-12). Pops `true` when something was saved.
class AdminActivityFormScreen extends StatefulWidget {
  const AdminActivityFormScreen({super.key, this.activity});

  /// Null to add a new activity.
  final AdminActivity? activity;

  @override
  State<AdminActivityFormScreen> createState() =>
      _AdminActivityFormScreenState();
}

/// Text fields, in form order: API name, label, lines.
const _textFields = [
  ('activity_name', 'Name', 1),
  ('developmental_goal', 'Developmental goal', 2),
  ('materials', 'Materials (write "None" if nothing is needed)', 1),
  ('description', 'How to do it', 5),
  ('cultural_relevance', 'Cultural relevance', 3),
  ('plain_aim', 'Plain aim, shown as "Its aim is to …" (optional)', 2),
  ('source_url', 'Source link (optional)', 1),
];

const _transitionLabels = {
  'under_review': ('Submit for review', Icons.rate_review_rounded),
  'published': ('Publish', Icons.public_rounded),
  'draft': ('Return to draft', Icons.undo_rounded),
};

class _AdminActivityFormScreenState extends State<AdminActivityFormScreen> {
  late final AdminService _service = AdminService(context.read<ApiClient>());
  final _formKey = GlobalKey<FormState>();
  final _scroll = ScrollController();
  late final Map<String, TextEditingController> _text = {
    for (final (field, _, _) in _textFields)
      field: TextEditingController(text: _initial(field)),
  };
  late final Map<String, String?> _picks = {
    'developmental_domain': widget.activity?.domain,
    'age_range': widget.activity?.ageRange,
    'difficulty_level': widget.activity?.difficulty,
    'source': widget.activity?.source,
  };

  AdminChoices? _choices;
  late AdminActivity? _activity = widget.activity;
  Map<String, List<String>> _fieldErrors = {};
  String? _error;
  String? _notice;
  bool _saving = false;
  bool _changed = false;

  bool get _isNew => _activity == null;

  String _initial(String field) {
    final a = widget.activity;
    if (a == null) return '';
    return switch (field) {
      'activity_name' => a.name,
      'developmental_goal' => a.goal,
      'materials' => a.materials,
      'description' => a.description,
      'cultural_relevance' => a.culturalRelevance,
      'plain_aim' => a.plainAim,
      _ => a.sourceUrl,
    };
  }

  @override
  void initState() {
    super.initState();
    _loadChoices();
  }

  @override
  void dispose() {
    for (final c in _text.values) {
      c.dispose();
    }
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _loadChoices() async {
    try {
      final choices = await _service.choices();
      if (mounted) setState(() => _choices = choices);
    } on ApiException catch (e) {
      if (mounted) await _failed(e);
    }
  }

  Future<void> _failed(ApiException e) async {
    if (e.statusCode == 401) {
      final auth = context.read<AuthState>();
      Navigator.of(context).popUntil((route) => route.isFirst);
      return auth.sessionExpired();
    }
    setState(() {
      _fieldErrors = e.fieldErrors;
      _error = e.fieldErrors.isEmpty
          ? e.message
          : 'Please check the highlighted fields.';
    });
    _showTop();
  }

  /// The notice and error sit at the top; Save is at the bottom.
  void _showTop() {
    if (_scroll.hasClients) {
      _scroll.animateTo(
        0,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  Map<String, String> _values() => {
    for (final e in _text.entries) e.key: e.value.text.trim(),
    for (final e in _picks.entries)
      if (e.value != null) e.key: e.value!,
  };

  Future<void> _save() async {
    setState(() {
      _error = null;
      _notice = null;
      _fieldErrors = {};
    });
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      final before = _activity?.status;
      final saved = _isNew
          ? await _service.create(_values())
          : await _service.update(_activity!.id, _values());
      if (!mounted) return;
      _changed = true;
      setState(() {
        _activity = saved;
        _notice = before == null
            ? 'Added as ${saved.activityId}, in Draft.'
            : before != saved.status
            ? 'Saved. It went back to Draft so the changes can be reviewed.'
            : 'Saved.';
      });
      _showTop();
    } on ApiException catch (e) {
      if (mounted) await _failed(e);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _move(String target) async {
    final a = _activity!;
    if (a.status == 'published' && target == 'draft') {
      final ok = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Unpublish this activity?'),
          content: const Text(
            'Caregivers will stop being given it until it is reviewed and '
            'published again.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            TextButton(
              key: const Key('confirmUnpublish'),
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Return to draft'),
            ),
          ],
        ),
      );
      if (ok != true) return;
    }
    setState(() {
      _saving = true;
      _error = null;
      _notice = null;
    });
    try {
      final moved = await _service.setStatus(a.id, target);
      if (!mounted) return;
      _changed = true;
      setState(() {
        _activity = moved;
        _notice =
            'Now ${moved.statusLabel}.'
            '${target == 'published' ? ' Update the search index on the dashboard so caregivers can be given it.' : ''}';
      });
      _showTop();
    } on ApiException catch (e) {
      if (mounted) await _failed(e);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final choices = _choices;
    final a = _activity;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) Navigator.of(context).pop(_changed);
      },
      child: Scaffold(
        appBar: NurturaAppBar(title: a == null ? 'Add activity' : a.activityId),
        body: SafeArea(
          child: choices == null && _error == null
              ? const Center(child: CircularProgressIndicator())
              : Form(
                  key: _formKey,
                  child: ListView(
                    key: const Key('activityForm'),
                    controller: _scroll,
                    padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
                    children: [
                      if (a != null) ...[
                        _StatusPanel(
                          activity: a,
                          transitions:
                              choices?.transitions[a.status] ?? const [],
                          busy: _saving,
                          onMove: _move,
                        ),
                        const SizedBox(height: 14),
                      ],
                      if (_notice != null) ...[
                        MessageBanner.success(
                          _notice!,
                          key: const Key('formNotice'),
                        ),
                        const SizedBox(height: 10),
                      ],
                      if (_error != null) ...[
                        MessageBanner.error(
                          _error!,
                          key: const Key('formError'),
                        ),
                        const SizedBox(height: 10),
                      ],
                      if (a != null && a.status != 'draft')
                        Padding(
                          padding: const EdgeInsets.only(bottom: 10),
                          child: MessageBanner.info(
                            'Saving changes sends this activity back to Draft '
                            'for review, so nothing reaches caregivers unreviewed.',
                          ),
                        ),
                      if (choices != null) ..._fields(choices),
                      const SizedBox(height: 16),
                      PrimaryButton(
                        key: const Key('saveActivityButton'),
                        label: a == null ? 'Add as draft' : 'Save changes',
                        icon: Icons.save_rounded,
                        loading: _saving,
                        onPressed: choices == null ? null : _save,
                      ),
                    ],
                  ),
                ),
        ),
      ),
    );
  }

  List<Widget> _fields(AdminChoices choices) {
    String? required(String? v) =>
        (v == null || v.trim().isEmpty) ? 'Required.' : null;
    Widget text(String field, String label, int lines) => Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextFormField(
        key: Key('field_$field'),
        controller: _text[field],
        minLines: lines,
        maxLines: lines == 1 ? 1 : lines + 3,
        decoration: InputDecoration(
          labelText: label,
          errorText: _fieldErrors[field]?.join(' '),
          errorMaxLines: 3,
        ),
        validator: field == 'plain_aim' || field == 'source_url'
            ? null
            : required,
      ),
    );
    Widget pick(String field, String label, List<Choice> options) => Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: DropdownButtonFormField<String>(
        key: Key('field_$field'),
        initialValue: _picks[field],
        isExpanded: true,
        decoration: InputDecoration(
          labelText: label,
          errorText: _fieldErrors[field]?.join(' '),
        ),
        items: [
          for (final o in options)
            DropdownMenuItem(value: o.value, child: Text(o.label)),
        ],
        onChanged: (v) => setState(() => _picks[field] = v),
        validator: (v) => v == null ? 'Required.' : null,
      ),
    );
    return [
      text('activity_name', 'Name', 1),
      pick('developmental_domain', 'Area', choices.domains),
      pick('age_range', 'Age', choices.ageRanges),
      pick('difficulty_level', 'Difficulty', choices.difficultyLevels),
      for (final (field, label, lines) in _textFields.skip(1))
        if (field != 'source_url') text(field, label, lines),
      pick('source', 'Source (whose guidance it follows)', choices.sources),
      text('source_url', 'Source link (optional)', 1),
    ];
  }
}

class _StatusPanel extends StatelessWidget {
  const _StatusPanel({
    required this.activity,
    required this.transitions,
    required this.busy,
    required this.onMove,
  });

  final AdminActivity activity;
  final List<String> transitions;
  final bool busy;
  final ValueChanged<String> onMove;

  @override
  Widget build(BuildContext context) {
    final a = activity;
    final p = context.palette;
    return AppCard(
      key: const Key('statusPanel'),
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(child: Text(a.name, style: AppText.quicksand(size: 18))),
              StatusPill(status: a.status, label: a.statusLabel),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 14,
            runSpacing: 4,
            children: [
              Text(
                'Recommended ${a.timesRecommended}×',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              Text(
                a.averageRating == null
                    ? 'No ratings yet'
                    : 'Rated ${a.averageRating}★ by ${a.feedbackCount}',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              if (a.status == 'published')
                Text(
                  a.searchable ? 'Searchable' : 'Not searchable yet',
                  style: AppText.nunito(
                    size: 12.5,
                    weight: FontWeight.w700,
                    color: a.searchable ? p.sage : p.rose,
                  ),
                ),
            ],
          ),
          if (transitions.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final t in transitions)
                  SecondaryButton(
                    key: Key('move_$t'),
                    label: _transitionLabels[t]?.$1 ?? t,
                    icon: _transitionLabels[t]?.$2,
                    onPressed: busy ? null : () => onMove(t),
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
