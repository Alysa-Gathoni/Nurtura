import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_theme.dart';
import '../../widgets/village.dart';
import 'admin_account_screen.dart';
import 'admin_activities_screen.dart';
import 'admin_dashboard_screen.dart';
import 'admin_feedback_screen.dart';

/// The administrator's home (#123): Dashboard, Activities, Feedback and
/// Account tabs. Caregivers never see these; the server refuses them too.
class AdminShell extends StatefulWidget {
  const AdminShell({super.key});

  @override
  State<AdminShell> createState() => _AdminShellState();
}

class _AdminShellState extends State<AdminShell> {
  // The fourth tab (3) is Account.
  static const dashboard = 0, activities = 1, feedback = 2;

  int _tab = dashboard;

  /// A status filter to open the Activities tab with (from the dashboard).
  String? _activityStatus;

  void _go(int tab) => setState(() {
    _tab = tab;
    if (tab != activities) _activityStatus = null;
  });

  void _openActivities(String? status) => setState(() {
    _tab = activities;
    _activityStatus = status;
  });

  @override
  Widget build(BuildContext context) {
    final (title, subtitle) = switch (_tab) {
      dashboard => ('Dashboard', 'How Nurtura is doing'),
      activities => ('Activities', 'The library caregivers are given'),
      feedback => ('Feedback', 'What caregivers said'),
      _ => ('Account', null),
    };
    return Scaffold(
      body: Column(
        children: [
          AdminHeader(title: title, subtitle: subtitle),
          Expanded(
            child: switch (_tab) {
              dashboard => AdminDashboardScreen(
                onOpenActivities: _openActivities,
              ),
              activities => AdminActivitiesScreen(
                key: ValueKey(_activityStatus),
                initialStatus: _activityStatus,
              ),
              feedback => const AdminFeedbackScreen(),
              _ => const AdminAccountScreen(),
            },
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: _go,
        destinations: const [
          NavigationDestination(
            key: Key('admin_tab_dashboard'),
            icon: Icon(Icons.space_dashboard_outlined),
            selectedIcon: Icon(Icons.space_dashboard_rounded),
            label: 'Dashboard',
          ),
          NavigationDestination(
            key: Key('admin_tab_activities'),
            icon: Icon(Icons.local_library_outlined),
            selectedIcon: Icon(Icons.local_library_rounded),
            label: 'Activities',
          ),
          NavigationDestination(
            key: Key('admin_tab_feedback'),
            icon: Icon(Icons.reviews_outlined),
            selectedIcon: Icon(Icons.reviews_rounded),
            label: 'Feedback',
          ),
          NavigationDestination(
            key: Key('admin_tab_account'),
            icon: Icon(Icons.person_outline_rounded),
            selectedIcon: Icon(Icons.person_rounded),
            label: 'Account',
          ),
        ],
      ),
    );
  }
}

/// The admin tabs' header, on the same watercolour wash as the caregiver
/// app, marked "Admin".
class AdminHeader extends StatelessWidget {
  const AdminHeader({super.key, required this.title, this.subtitle});

  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return VillageWash(
      seed: title.length + 3,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 18),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const VillageMark(size: 34),
                  const SizedBox(width: 10),
                  Text(
                    'Nurtura',
                    style: AppText.quicksand(size: 18, color: p.ink),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    key: const Key('adminBadge'),
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: p.primarySoft,
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      'ADMIN',
                      style: AppText.nunito(
                        size: 11,
                        weight: FontWeight.w900,
                        color: p.primary,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              Text(title, style: AppText.quicksand(size: 28, color: p.ink)),
              if (subtitle != null)
                Text(
                  subtitle!,
                  style: AppText.nunito(
                    size: 14.5,
                    weight: FontWeight.w600,
                    color: p.mutedText,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
