import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/app_lock.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// The "Unlock with fingerprint" switch (#150). Hidden on phones with no
/// fingerprint or face set up. Turning it on needs one successful scan.
class FingerprintLockTile extends StatelessWidget {
  const FingerprintLockTile({super.key});

  @override
  Widget build(BuildContext context) {
    final lock = context.watch<AppLock>();
    if (!lock.available) return const SizedBox.shrink();
    final p = context.palette;
    return SwitchListTile.adaptive(
      key: const Key('fingerprintLockSwitch'),
      contentPadding: EdgeInsets.zero,
      secondary: Icon(Icons.fingerprint_rounded, color: p.primary),
      value: lock.enabled,
      title: Text(
        'Unlock with fingerprint',
        style: AppText.nunito(size: 15, weight: FontWeight.w700, color: p.ink),
      ),
      subtitle: Text(
        'Ask for your fingerprint when Nurtura opens.',
        style: Theme.of(context).textTheme.bodySmall,
      ),
      onChanged: (on) async {
        if (!on) return lock.disable();
        final messenger = ScaffoldMessenger.of(context);
        final ok = await lock.enable();
        messenger.showSnackBar(
          SnackBar(
            content: Text(
              ok
                  ? 'Nurtura will ask for your fingerprint when it opens.'
                  : lock.error ?? "Fingerprint lock wasn't turned on.",
            ),
          ),
        );
      },
    );
  }
}
