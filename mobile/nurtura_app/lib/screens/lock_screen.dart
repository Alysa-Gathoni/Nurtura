import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_lock.dart';
import '../state/auth_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';
import '../widgets/village.dart';

/// Shown instead of the app while "Unlock with fingerprint" is on and the
/// app is locked (#150). The phone's prompt opens straight away.
class LockScreen extends StatefulWidget {
  const LockScreen({super.key});

  @override
  State<LockScreen> createState() => _LockScreenState();
}

class _LockScreenState extends State<LockScreen> {
  bool _checking = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _unlock());
  }

  Future<void> _unlock() async {
    if (_checking || !mounted) return;
    setState(() => _checking = true);
    await context.read<AppLock>().unlock();
    if (mounted) setState(() => _checking = false);
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final lock = context.watch<AppLock>();
    final email = context.watch<AuthState>().user?.email;
    return Scaffold(
      key: const Key('lockScreen'),
      body: VillageWash(
        seed: 7,
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(28),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 400),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Center(child: VillageMark(size: 96)),
                    const SizedBox(height: 18),
                    Text(
                      'Nurtura is locked',
                      textAlign: TextAlign.center,
                      style: AppText.quicksand(size: 28, color: p.ink),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      email == null
                          ? 'Use your fingerprint to open it.'
                          : 'Use your fingerprint to open $email.',
                      textAlign: TextAlign.center,
                      style: AppText.nunito(
                        size: 15.5,
                        weight: FontWeight.w600,
                        color: p.mutedText,
                      ),
                    ),
                    const SizedBox(height: 32),
                    Center(
                      child: Material(
                        color: p.primarySoft,
                        shape: const CircleBorder(),
                        child: InkWell(
                          key: const Key('fingerprintButton'),
                          customBorder: const CircleBorder(),
                          onTap: _checking ? null : _unlock,
                          child: Padding(
                            padding: const EdgeInsets.all(22),
                            child: Icon(
                              Icons.fingerprint_rounded,
                              size: 64,
                              color: p.primary,
                              semanticLabel: 'Unlock with fingerprint',
                            ),
                          ),
                        ),
                      ),
                    ),
                    if (lock.error != null) ...[
                      const SizedBox(height: 20),
                      MessageBanner.error(
                        lock.error!,
                        key: const Key('lockError'),
                      ),
                    ],
                    const SizedBox(height: 28),
                    PrimaryButton(
                      key: const Key('unlockButton'),
                      label: 'Unlock with fingerprint',
                      icon: Icons.fingerprint_rounded,
                      loading: _checking,
                      onPressed: _unlock,
                    ),
                    const SizedBox(height: 8),
                    TextButton(
                      key: const Key('usePasswordInstead'),
                      // Logging out also turns the lock off (AppLock.forget),
                      // so a broken sensor never traps the account.
                      onPressed: _checking
                          ? null
                          : () => context.read<AuthState>().logout(),
                      child: const Text('Use password instead'),
                    ),
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
