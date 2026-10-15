import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/child_profile.dart';
import '../state/children_state.dart';
import '../widgets/shell_header.dart';
import 'child_form_screen.dart';
import 'children_screen.dart';
import 'milestone_screen.dart';
import 'progress_screen.dart';
import 'recommendations_screen.dart';

/// The signed-in home: Today (ideas), Progress, Milestones and Family tabs
/// for the selected child.
class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  static const today = 0, progress = 1, milestones = 2, family = 3;

  int _tab = today;

  /// Shows the "profile saved" banner on the Milestones tab once.
  bool _justCreated = false;

  /// Bumped to make the Today tab ask for a fresh batch (after a milestone).
  int _ideasGeneration = 0;
  bool _refreshIdeas = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final children = context.read<ChildrenState>();
      if (!children.loaded && !children.loading) children.load();
    });
  }

  void _go(int tab) => setState(() {
    _tab = tab;
    if (tab != milestones) _justCreated = false;
    _refreshIdeas = false;
  });

  void _childAdded(ChildProfile child) {
    context.read<ChildrenState>().select(child);
    setState(() {
      _tab = milestones;
      _justCreated = true;
    });
  }

  Future<void> _addChild() async {
    final child = await Navigator.of(context).push<ChildProfile>(
      MaterialPageRoute(builder: (_) => const ChildFormScreen()),
    );
    if (child != null && mounted) _childAdded(child);
  }

  void _seeIdeas() => setState(() {
    _tab = today;
    _justCreated = false;
    _refreshIdeas = true;
    _ideasGeneration++;
  });

  void _openChild(ChildProfile child) {
    context.read<ChildrenState>().select(child);
    _go(today);
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<ChildrenState>();
    final child = state.selected;
    // Until there's a child, the family screen handles loading, errors and
    // adding the first one.
    if (!state.loaded || child == null) {
      return ChildrenScreen(onChildAdded: _childAdded);
    }

    final (title, subtitle) = switch (_tab) {
      today => (
        'From the village',
        child.isExpecting
            ? 'Gentle ideas for your pregnancy'
            : 'Picked for ${child.name}',
      ),
      progress => ('Progress', 'Every step counts'),
      milestones => ('Milestones', 'What can ${child.name} do?'),
      _ => ('Family', null),
    };

    return Scaffold(
      body: Column(
        children: [
          ShellHeader(
            title: title,
            subtitle: subtitle,
            showChild: _tab != family,
            onAddChild: _addChild,
          ),
          Expanded(
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 220),
              child: KeyedSubtree(
                key: ValueKey('$_tab-${child.id}-$_ideasGeneration'),
                child: switch (_tab) {
                  today => RecommendationsScreen(
                    child: child,
                    embedded: true,
                    refresh: _refreshIdeas,
                  ),
                  progress => ProgressScreen(
                    child: child,
                    onRecord: () => _go(milestones),
                  ),
                  milestones => MilestoneScreen(
                    child: child,
                    embedded: true,
                    justCreated: _justCreated,
                    onSeeIdeas: _seeIdeas,
                  ),
                  _ => ChildrenScreen(
                    embedded: true,
                    onOpenChild: _openChild,
                    onChildAdded: _childAdded,
                  ),
                },
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: _go,
        destinations: const [
          NavigationDestination(
            key: Key('tab_today'),
            icon: Icon(Icons.wb_sunny_outlined),
            selectedIcon: Icon(Icons.wb_sunny_rounded),
            label: 'Today',
          ),
          NavigationDestination(
            key: Key('tab_progress'),
            icon: Icon(Icons.emoji_events_outlined),
            selectedIcon: Icon(Icons.emoji_events_rounded),
            label: 'Progress',
          ),
          NavigationDestination(
            key: Key('tab_milestones'),
            icon: Icon(Icons.checklist_rounded),
            selectedIcon: Icon(Icons.fact_check_rounded),
            label: 'Milestones',
          ),
          NavigationDestination(
            key: Key('tab_family'),
            icon: Icon(Icons.family_restroom_outlined),
            selectedIcon: Icon(Icons.family_restroom_rounded),
            label: 'Family',
          ),
        ],
      ),
    );
  }
}
