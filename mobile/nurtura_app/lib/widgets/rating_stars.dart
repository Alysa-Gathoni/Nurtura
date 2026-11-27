import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// Five stars for "How helpful was this idea?"; tappable when [onRate] is
/// set, read-only otherwise. Used by the feedback sheet and the saved summary.
class RatingStars extends StatelessWidget {
  const RatingStars({
    super.key,
    required this.rating,
    this.onRate,
    this.keyPrefix = 'star',
  });

  final int rating;
  final ValueChanged<int>? onRate;

  /// Each star is keyed `<keyPrefix>_<n>`; the saved summary uses its own
  /// prefix so that it doesn't clash with the sheet opened over it.
  final String keyPrefix;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Row(
      children: [
        for (var i = 1; i <= 5; i++)
          IconButton(
            key: Key('${keyPrefix}_$i'),
            tooltip: '$i out of 5',
            visualDensity: VisualDensity.compact,
            onPressed: onRate == null ? null : () => onRate!(i),
            icon: Icon(
              i <= rating ? Icons.star_rounded : Icons.star_outline_rounded,
              color: i <= rating ? p.mustard : p.mutedText,
              size: 32,
            ),
            disabledColor: i <= rating ? p.mustard : p.mutedText,
          ),
      ],
    );
  }
}
