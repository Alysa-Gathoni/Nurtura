import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// Pill-shaped two-or-more option switch on a mint track.
class SegmentedToggle extends StatelessWidget {
  const SegmentedToggle({
    super.key,
    required this.options,
    required this.selected,
    required this.onChanged,
  });

  final List<String> options;
  final int selected;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: const ShapeDecoration(
        color: AppColors.mint,
        shape: StadiumBorder(),
      ),
      child: Row(
        children: [
          for (var i = 0; i < options.length; i++)
            Expanded(
              child: Material(
                key: Key('toggle_${options[i]}'),
                color: i == selected ? AppColors.tealDeep : Colors.transparent,
                shape: const StadiumBorder(),
                child: InkWell(
                  customBorder: const StadiumBorder(),
                  onTap: () => onChanged(i),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 10),
                    child: Text(
                      options[i],
                      textAlign: TextAlign.center,
                      style: AppText.nunito(
                        size: 15,
                        weight: FontWeight.w800,
                        color: i == selected
                            ? Colors.white
                            : AppColors.tealDeep,
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
