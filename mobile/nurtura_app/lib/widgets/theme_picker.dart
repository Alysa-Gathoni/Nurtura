import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/theme_state.dart';
import 'segmented_toggle.dart';

/// System / Light / Dark, remembered on the phone. Used on the caregiver
/// Family tab and the administrator Account tab.
class ThemePicker extends StatelessWidget {
  const ThemePicker({super.key});

  static const _modes = [ThemeMode.system, ThemeMode.light, ThemeMode.dark];

  @override
  Widget build(BuildContext context) {
    final theme = context.watch<ThemeState>();
    return SegmentedToggle(
      key: const Key('themePicker'),
      options: const ['System', 'Light', 'Dark'],
      icons: const [
        Icons.brightness_auto_rounded,
        Icons.light_mode_rounded,
        Icons.dark_mode_rounded,
      ],
      selected: _modes.indexOf(theme.mode),
      onChanged: (i) => theme.set(_modes[i]),
    );
  }
}
