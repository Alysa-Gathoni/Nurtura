import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/child_profile.dart';
import '../services/api_client.dart';
import '../state/children_state.dart';
import '../state/recommendation_cache.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/domain_style.dart';
import '../utils/dates.dart';
import '../widgets/app_card.dart';
import '../widgets/app_text_field.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';
import '../widgets/nurtura_app_bar.dart';
import '../widgets/pill_chip.dart';
import '../widgets/segmented_toggle.dart';

/// Creates a child profile, or edits [child]'s (#134); pops with the saved
/// child. When editing, the profile can also be deleted: the screen then
/// pops with null.
class ChildFormScreen extends StatefulWidget {
  const ChildFormScreen({super.key, this.child});

  /// The child being edited; null to add a new one.
  final ChildProfile? child;

  @override
  State<ChildFormScreen> createState() => _ChildFormScreenState();
}

class _ChildFormScreenState extends State<ChildFormScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _interest = TextEditingController();
  final _dateFocus = FocusNode();

  bool _expecting = false;
  DateTime? _date;
  final _interests = <String>[];
  final _concerns = <String>{};

  bool _submitting = false;
  bool _deleting = false;
  bool _dateMissing = false;
  ApiException? _error;

  bool get _editing => widget.child != null;

  @override
  void initState() {
    super.initState();
    final child = widget.child;
    if (child != null) {
      _name.text = child.name;
      _expecting = child.isExpecting;
      _date = child.dateOfBirth;
      _interests.addAll(child.interests);
      _concerns.addAll(child.concerns);
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _interest.dispose();
    _dateFocus.dispose();
    super.dispose();
  }

  void _setExpecting(bool expecting) {
    if (expecting == _expecting) return;
    setState(() {
      _expecting = expecting;
      _date = null; // a birth date isn't a valid due date, and vice versa
    });
  }

  Future<void> _pickDate() async {
    // Closing the picker gives the focus back to whatever had it, so the
    // next thing typed (an interest) went into the name (#138). The date
    // field takes the focus first, so that's where it comes back to.
    _dateFocus.requestFocus();
    final now = today();
    final first = _expecting
        ? now.add(const Duration(days: 1))
        : DateTime(now.year - 6, now.month, now.day);
    final last = _expecting ? now.add(const Duration(days: 300)) : now;
    final initial =
        _date ??
        (_expecting
            ? now.add(const Duration(days: 90))
            : DateTime(now.year, now.month - 6, now.day));
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: first,
      lastDate: last,
      helpText: _expecting ? 'Expected due date' : 'Date of birth',
    );
    if (picked != null) {
      setState(() {
        _date = picked;
        _dateMissing = false;
      });
    }
  }

  void _addInterest() {
    final value = _interest.text.trim();
    if (value.isEmpty) return;
    setState(() {
      if (!_interests.any((i) => i.toLowerCase() == value.toLowerCase())) {
        _interests.add(value);
      }
      _interest.clear();
    });
  }

  Future<void> _save() async {
    if (_submitting || _deleting) return;
    _addInterest(); // keep anything typed but not yet added
    final valid = _formKey.currentState!.validate();
    setState(() {
      _error = null;
      _dateMissing = _date == null;
    });
    if (!valid || _date == null) return;

    setState(() => _submitting = true);
    try {
      final children = context.read<ChildrenState>();
      final concerns = developmentalDomains.where(_concerns.contains).toList();
      final child = _editing
          ? await children.update(
              widget.child!,
              name: _name.text,
              dateOfBirth: _date!,
              interests: List.of(_interests),
              concerns: concerns,
            )
          : await children.create(
              name: _name.text,
              dateOfBirth: _date!,
              interests: List.of(_interests),
              concerns: concerns,
            );
      if (mounted) Navigator.of(context).pop(child);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _delete() async {
    if (_submitting || _deleting) return;
    final child = widget.child!;
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text("Delete ${child.name}'s profile?"),
        content: const Text(
          'Their milestones, ideas and ratings are deleted too. '
          "This can't be undone.",
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            key: const Key('confirmDeleteChild'),
            style: TextButton.styleFrom(foregroundColor: context.palette.rose),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    setState(() {
      _deleting = true;
      _error = null;
    });
    try {
      final cache = context.read<RecommendationCache>();
      await context.read<ChildrenState>().delete(child);
      await cache.remove(child.id);
      if (mounted) Navigator.of(context).pop();
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _deleting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    const shownFields = {'name', 'date_of_birth', 'interests', 'concerns'};
    String? banner;
    if (_error != null) {
      final other = [
        for (final e in _error!.fieldErrors.entries)
          if (!shownFields.contains(e.key)) ...e.value,
      ];
      final anyShown = _error!.fieldErrors.keys.any(shownFields.contains);
      final parts = [if (!anyShown) _error!.message, ...other];
      banner = parts.isEmpty ? null : parts.join(' ');
    }
    final dateError =
        _error?.field('date_of_birth') ??
        (_dateMissing
            ? (_expecting
                  ? 'Choose the expected due date.'
                  : 'Choose the date of birth.')
            : null);

    return Scaffold(
      appBar: NurturaAppBar(title: _editing ? 'Edit profile' : 'Add a child'),
      body: SafeArea(
        child: Align(
          alignment: Alignment.topCenter,
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 520),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    AppCard(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          AppTextField(
                            key: const Key('childNameField'),
                            label: "Child's name",
                            hint: 'e.g. Amani',
                            controller: _name,
                            prefixIcon: Icons.child_care_rounded,
                            textInputAction: TextInputAction.next,
                            errorText: _error?.field('name'),
                            validator: (v) => (v == null || v.trim().isEmpty)
                                ? "Enter your child's name."
                                : null,
                          ),
                          const SizedBox(height: 18),
                          SegmentedToggle(
                            options: const ['Born', 'Expecting'],
                            selected: _expecting ? 1 : 0,
                            onChanged: (i) => _setExpecting(i == 1),
                          ),
                          const SizedBox(height: 14),
                          _DateField(
                            label: _expecting
                                ? 'Expected due date'
                                : 'Date of birth',
                            value: _date,
                            errorText: dateError,
                            focusNode: _dateFocus,
                            onTap: _pickDate,
                          ),
                          if (_expecting) ...[
                            const SizedBox(height: 10),
                            const MessageBanner.info(
                              "We'll suggest pregnancy activities until your "
                              'baby arrives.',
                            ),
                          ],
                        ],
                      ),
                    ),
                    const SizedBox(height: 16),
                    AppCard(
                      padding: const EdgeInsets.all(18),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          AppTextField(
                            key: const Key('interestField'),
                            label: 'Interests',
                            hint: 'e.g. music, animals, water play',
                            controller: _interest,
                            prefixIcon: Icons.star_rounded,
                            errorText: _error?.field('interests'),
                            onSubmitted: (_) => _addInterest(),
                            suffix: IconButton(
                              key: const Key('addInterestButton'),
                              tooltip: 'Add interest',
                              icon: Icon(
                                Icons.add_circle_rounded,
                                color: context.palette.primary,
                              ),
                              onPressed: _addInterest,
                            ),
                          ),
                          if (_interests.isNotEmpty) ...[
                            const SizedBox(height: 10),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: [
                                for (final interest in _interests)
                                  PillChip(
                                    key: Key('interest_$interest'),
                                    label: interest,
                                    color: context.palette.mustard,
                                    background: context.palette.mustardSoft,
                                    icon: Icons.star_rounded,
                                    trailingIcon: Icons.close_rounded,
                                    onTap: () => setState(
                                      () => _interests.remove(interest),
                                    ),
                                  ),
                              ],
                            ),
                          ],
                          const SizedBox(height: 20),
                          Text(
                            "Areas you'd like support with",
                            style: AppText.nunito(
                              size: 13.5,
                              weight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            "Optional. We'll give these areas more attention.",
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 10),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: [
                              for (final domain in developmentalDomains)
                                DomainChip(
                                  domain,
                                  key: Key('concern_$domain'),
                                  selected: _concerns.contains(domain),
                                  onTap: () => setState(() {
                                    if (!_concerns.remove(domain)) {
                                      _concerns.add(domain);
                                    }
                                  }),
                                ),
                            ],
                          ),
                          if (_error?.field('concerns') != null) ...[
                            const SizedBox(height: 8),
                            Text(
                              _error!.field('concerns')!,
                              style: AppText.nunito(
                                size: 12.5,
                                weight: FontWeight.w700,
                                color: context.palette.rose,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    if (banner != null) ...[
                      const SizedBox(height: 16),
                      MessageBanner.error(banner, key: const Key('childError')),
                    ],
                    const SizedBox(height: 20),
                    PrimaryButton(
                      key: const Key('saveChildButton'),
                      label: 'Save profile',
                      icon: Icons.check_rounded,
                      loading: _submitting,
                      onPressed: _deleting ? null : _save,
                    ),
                    if (_editing) ...[
                      const SizedBox(height: 14),
                      Center(
                        child: TextButton.icon(
                          key: const Key('deleteChildButton'),
                          style: TextButton.styleFrom(
                            foregroundColor: context.palette.rose,
                          ),
                          onPressed: _submitting || _deleting ? null : _delete,
                          icon: _deleting
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2.2,
                                  ),
                                )
                              : const Icon(Icons.delete_outline_rounded),
                          label: const Text('Delete this profile'),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Tappable field that opens a date picker, styled like [AppTextField].
class _DateField extends StatelessWidget {
  const _DateField({
    required this.label,
    required this.value,
    required this.onTap,
    this.errorText,
    this.focusNode,
  });

  final String label;
  final DateTime? value;
  final VoidCallback onTap;
  final String? errorText;
  final FocusNode? focusNode;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 6),
          child: Text(
            label,
            style: AppText.nunito(size: 13.5, weight: FontWeight.w800),
          ),
        ),
        InkWell(
          key: const Key('dateField'),
          focusNode: focusNode,
          borderRadius: BorderRadius.circular(AppRadii.field),
          onTap: onTap,
          child: InputDecorator(
            isEmpty: value == null,
            decoration: InputDecoration(
              prefixIcon: Icon(
                Icons.calendar_month_rounded,
                color: context.palette.mutedText,
              ),
              hintText: 'Choose a date',
              errorText: errorText,
            ),
            child: value == null
                ? null
                : Text(
                    formatDate(value!),
                    style: AppText.nunito(size: 15.5, weight: FontWeight.w600),
                  ),
          ),
        ),
      ],
    );
  }
}
