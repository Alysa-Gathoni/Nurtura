import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// Pill-shaped two-or-more option switch on a soft track.
class SegmentedToggle extends StatelessWidget {
  const SegmentedToggle({
    super.key,
    required this.options,
    required this.selected,
    required this.onChanged,
    this.icons,
  });

  final List<String> options;
  final int selected;
  final ValueChanged<int> onChanged;

  /// Optional icon per option.
  final List<IconData>? icons;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: ShapeDecoration(color: p.mint, shape: const StadiumBorder()),
      child: Row(
        children: [
          for (var i = 0; i < options.length; i++)
            Expanded(
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 220),
                curve: Curves.easeOut,
                decoration: ShapeDecoration(
                  color: i == selected ? p.tealDeep : Colors.transparent,
                  shape: const StadiumBorder(),
                ),
                child: Material(
                  key: Key('toggle_${options[i]}'),
                  color: Colors.transparent,
                  shape: const StadiumBorder(),
                  child: InkWell(
                    customBorder: const StadiumBorder(),
                    onTap: () => onChanged(i),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          if (icons != null) ...[
                            Icon(
                              icons![i],
                              size: 16,
                              color: i == selected ? p.onPrimary : p.tealDeep,
                            ),
                            const SizedBox(width: 6),
                          ],
                          Flexible(
                            child: Text(
                              options[i],
                              textAlign: TextAlign.center,
                              overflow: TextOverflow.ellipsis,
                              style: AppText.nunito(
                                size: 15,
                                weight: FontWeight.w800,
                                color: i == selected ? p.onPrimary : p.tealDeep,
                              ),
                            ),
                          ),
                        ],
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
