import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/auth_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../widgets/app_card.dart';
import '../widgets/nurtura_app_bar.dart';

/// Signed-in landing screen. Child profiles arrive in #24.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthState>();
    return Scaffold(
      appBar: NurturaAppBar(
        title: 'Nurtura',
        actions: [
          IconButton(
            key: const Key('logoutButton'),
            tooltip: 'Log out',
            icon: const Icon(Icons.logout_rounded),
            onPressed: auth.logout,
          ),
        ],
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: AppCard(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(
                  Icons.verified_rounded,
                  color: AppColors.teal,
                  size: 40,
                ),
                const SizedBox(height: 10),
                Text('You\'re signed in', style: AppText.quicksand(size: 22)),
                const SizedBox(height: 4),
                Text(
                  auth.user?.email ?? '',
                  key: const Key('signedInEmail'),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
