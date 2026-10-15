import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../logic/progress.dart';
import '../models/child_profile.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// A child's initial in a flat earthy circle (mustard while expecting).
class ChildAvatar extends StatelessWidget {
  const ChildAvatar({super.key, required this.child, this.size = 48});

  final ChildProfile child;
  final double size;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    // A flat earthy colour per child, steady across launches.
    final colours = [p.sage, p.primaryMid, p.dusk, p.plum];
    final colour = child.isExpecting
        ? p.mustard
        : colours[child.name.codeUnits.fold(0, (a, b) => a + b) %
              colours.length];
    return Container(
      width: size,
      height: size,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: colour,
        border: Border.all(color: p.card, width: 2),
      ),
      child: child.isExpecting
          ? Icon(Icons.favorite_rounded, color: p.card, size: size * 0.45)
          : Text(
              child.name.isEmpty ? '?' : child.name[0].toUpperCase(),
              style: AppText.quicksand(size: size * 0.42, color: p.card),
            ),
    );
  }
}

/// "3-day streak" with a flame; grey until the first day is checked.
class StreakChip extends StatelessWidget {
  const StreakChip({super.key, required this.days, this.onDark = false});

  final int days;

  /// On the coloured header, use a translucent white pill.
  final bool onDark;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final active = days > 0;
    return Semantics(
      label: active ? '$days-day streak' : 'No streak yet',
      child: Container(
        key: const Key('streakChip'),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: ShapeDecoration(
          shape: const StadiumBorder(),
          color: onDark ? Colors.white.withValues(alpha: 0.18) : p.mustardSoft,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.local_fire_department_rounded,
              size: 18,
              color: active
                  ? p.mustard
                  : (onDark ? Colors.white70 : p.mutedText),
            ),
            const SizedBox(width: 4),
            Text(
              '$days',
              style: AppText.nunito(
                size: 14,
                weight: FontWeight.w900,
                color: onDark ? Colors.white : p.ink,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// A ring that fills to [value] (0-1), animated, with [child] inside.
class ProgressRing extends StatelessWidget {
  const ProgressRing({
    super.key,
    required this.value,
    required this.color,
    this.size = 64,
    this.stroke = 7,
    this.child,
  });

  final double value;
  final Color color;
  final double size;
  final double stroke;
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    final track = context.palette.cardAlt;
    return SizedBox(
      width: size,
      height: size,
      child: TweenAnimationBuilder<double>(
        tween: Tween(begin: 0, end: value.clamp(0, 1)),
        duration: const Duration(milliseconds: 900),
        curve: Curves.easeOutCubic,
        builder: (context, v, inner) => CustomPaint(
          painter: _RingPainter(v, color, track, stroke),
          child: Center(child: inner),
        ),
        child: child,
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter(this.value, this.color, this.track, this.stroke);

  final double value;
  final Color color;
  final Color track;
  final double stroke;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final inset = rect.deflate(stroke / 2);
    final base = Paint()
      ..color = track
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke;
    canvas.drawArc(inset, 0, math.pi * 2, false, base);
    if (value <= 0) return;
    final arc = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeWidth = stroke;
    canvas.drawArc(inset, -math.pi / 2, math.pi * 2 * value, false, arc);
  }

  @override
  bool shouldRepaint(_RingPainter old) =>
      old.value != value || old.color != color || old.track != track;
}

const _badgeIcons = {
  'flag': Icons.flag_rounded,
  'celebration': Icons.celebration_rounded,
  'explore': Icons.explore_rounded,
  'visibility': Icons.visibility_rounded,
  'fire': Icons.local_fire_department_rounded,
  'star': Icons.star_rounded,
};

/// One badge: bright when unlocked, a soft outline with a hint when not.
class BadgeTile extends StatelessWidget {
  const BadgeTile({super.key, required this.badge});

  final AchievementBadge badge;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final on = badge.unlocked;
    return Semantics(
      label: '${badge.title}: ${on ? 'unlocked' : badge.howTo}',
      child: Column(
        key: Key('badge_${badge.id}'),
        children: [
          AnimatedScale(
            scale: on ? 1 : 0.92,
            duration: const Duration(milliseconds: 400),
            curve: Curves.elasticOut,
            child: Container(
              width: 62,
              height: 62,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: on ? p.mustard : p.cardAlt,
                border: Border.all(
                  color: on ? p.mustardSoft : p.border,
                  width: on ? 4 : 2,
                ),
              ),
              child: Icon(
                on ? _badgeIcons[badge.icon] : Icons.lock_rounded,
                color: on ? p.card : p.mutedText,
                size: on ? 30 : 22,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            badge.title,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppText.nunito(
              size: 12.5,
              weight: FontWeight.w800,
              color: on ? p.ink : p.mutedText,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            on ? 'Unlocked' : badge.howTo,
            textAlign: TextAlign.center,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: AppText.nunito(size: 11, color: p.mutedText),
          ),
        ],
      ),
    );
  }
}
