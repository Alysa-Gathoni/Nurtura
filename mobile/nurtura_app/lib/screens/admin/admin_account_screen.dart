import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../state/auth_state.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_theme.dart';
import '../../widgets/app_card.dart';
import '../../widgets/buttons.dart';
import '../../widgets/fingerprint_lock_tile.dart';
import '../../widgets/theme_picker.dart';
import '../change_password_screen.dart';

/// The administrator's account: who is signed in, theme and log out.
class AdminAccountScreen extends StatelessWidget {
  const AdminAccountScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthState>();
    final p = context.palette;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 28),
      children: [
        AppCard(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              CircleAvatar(
                radius: 22,
                backgroundColor: p.primary,
                child: Icon(
                  Icons.admin_panel_settings_rounded,
                  color: p.onPrimary,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      auth.user?.email ?? 'Administrator',
                      key: const Key('adminEmail'),
                      style: AppText.nunito(size: 15, weight: FontWeight.w800),
                    ),
                    Text(
                      'Administrator',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 10),
        SecondaryButton(
          key: const Key('passwordSettingsButton'),
          label: 'Change password',
          icon: Icons.lock_reset_rounded,
          onPressed: () => openPasswordSettings(context),
        ),
        const SizedBox(height: 4),
        const FingerprintLockTile(),
        const SizedBox(height: 22),
        Text('Appearance', style: AppText.quicksand(size: 20)),
        const SizedBox(height: 10),
        const ThemePicker(),
        const SizedBox(height: 22),
        Text(
          'Users, sign-in tokens and milestone verification are managed in '
          'the web admin.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 22),
        SecondaryButton(
          key: const Key('logoutButton'),
          label: 'Log out',
          icon: Icons.logout_rounded,
          onPressed: () => context.read<AuthState>().logout(),
        ),
      ],
    );
  }
}
