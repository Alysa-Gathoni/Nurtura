import 'package:flutter/material.dart';

import '../models/child_profile.dart';
import 'milestone_screen.dart';
import 'milestone_tracker_screen.dart';

/// The Milestones tab: the tracker (#192) or the catalogue picker.
///
/// It opens on the tracker, except straight after a profile is created,
/// when it opens on the picker so the caregiver can record what the child
/// can already do.
class MilestonesTab extends StatefulWidget {
  const MilestonesTab({
    super.key,
    required this.child,
    this.justCreated = false,
    this.onSeeIdeas,
  });

  final ChildProfile child;
  final bool justCreated;
  final VoidCallback? onSeeIdeas;

  @override
  State<MilestonesTab> createState() => _MilestonesTabState();
}

enum _View { tracker, record }

class _MilestonesTabState extends State<MilestonesTab> {
  late _View _view = widget.justCreated ? _View.record : _View.tracker;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 4),
          child: SizedBox(
            width: double.infinity,
            child: SegmentedButton<_View>(
              segments: const [
                ButtonSegment(
                  value: _View.tracker,
                  icon: Icon(Icons.timeline_rounded),
                  label: Text('Tracker', key: Key('milestonesTrackerSegment')),
                ),
                ButtonSegment(
                  value: _View.record,
                  icon: Icon(Icons.add_task_rounded),
                  label: Text('Record', key: Key('milestonesRecordSegment')),
                ),
              ],
              selected: {_view},
              onSelectionChanged: (s) => setState(() => _view = s.first),
            ),
          ),
        ),
        Expanded(
          child: switch (_view) {
            _View.tracker => MilestoneTrackerScreen(
              key: ValueKey('tracker-${widget.child.id}'),
              child: widget.child,
              onLogAnother: () => setState(() => _view = _View.record),
            ),
            _View.record => MilestoneScreen(
              child: widget.child,
              embedded: true,
              justCreated: widget.justCreated,
              onSeeIdeas: widget.onSeeIdeas,
            ),
          },
        ),
      ],
    );
  }
}
