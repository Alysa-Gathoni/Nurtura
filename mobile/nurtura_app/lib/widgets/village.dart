import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/app_colors.dart';

/// A soft watercolour wash behind a header: a few organic blobs in the
/// village colours, fading into the page. Deterministic, so it doesn't
/// shimmer between rebuilds.
class VillageWash extends StatelessWidget {
  const VillageWash({super.key, required this.child, this.seed = 1});

  final Widget child;

  /// Varies the blob layout between screens.
  final int seed;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final dark = Theme.of(context).brightness == Brightness.dark;
    return CustomPaint(
      painter: _WashPainter(
        seed: seed,
        colors: [p.sage, p.mustard, p.primaryLight],
        ground: p.paper,
        strength: dark ? 0.09 : 0.2,
      ),
      child: child,
    );
  }
}

class _WashPainter extends CustomPainter {
  _WashPainter({
    required this.seed,
    required this.colors,
    required this.ground,
    required this.strength,
  });

  final int seed;
  final List<Color> colors;

  /// The page colour the wash fades into at the bottom.
  final Color ground;
  final double strength;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.clipRect(Offset.zero & size);

    // Watercolour blobs: each painted twice, slightly offset, with soft
    // edges, so the overlap darkens like pigment does.
    final rnd = math.Random(seed);
    final anchors = [
      Offset(size.width * (0.82 + rnd.nextDouble() * 0.1), size.height * 0.18),
      Offset(size.width * (0.05 + rnd.nextDouble() * 0.12), size.height * 0.95),
      Offset(size.width * (0.55 + rnd.nextDouble() * 0.15), size.height * 1.05),
    ];
    for (var i = 0; i < anchors.length; i++) {
      final radius = size.shortestSide * (0.55 + rnd.nextDouble() * 0.35);
      final path = _blob(anchors[i], radius, rnd);
      final colour = colors[i % colors.length];
      for (final (shift, alpha) in [
        (Offset.zero, strength),
        (Offset(radius * 0.08, -radius * 0.05), strength * 0.6),
      ]) {
        canvas.drawPath(
          path.shift(shift),
          Paint()
            ..color = colour.withValues(alpha: alpha)
            ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 14),
        );
      }
    }

    // Fade into the page at the bottom, so the wash has no hard edge.
    final fade = Rect.fromLTWH(
      0,
      size.height * 0.55,
      size.width,
      size.height * 0.45,
    );
    canvas.drawRect(
      fade,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [ground.withValues(alpha: 0), ground],
        ).createShader(fade),
    );
    canvas.restore();
  }

  /// A closed, lumpy circle through 7 jittered points.
  static Path _blob(Offset centre, double radius, math.Random rnd) {
    const points = 7;
    final pts = [
      for (var i = 0; i < points; i++)
        () {
          final angle = i / points * 2 * math.pi;
          final r = radius * (0.78 + rnd.nextDouble() * 0.3);
          return centre + Offset(math.cos(angle) * r, math.sin(angle) * r);
        }(),
    ];
    final path = Path();
    for (var i = 0; i < points; i++) {
      final a = pts[i];
      final b = pts[(i + 1) % points];
      final mid = Offset((a.dx + b.dx) / 2, (a.dy + b.dy) / 2);
      if (i == 0) {
        final prev = pts[points - 1];
        path.moveTo((prev.dx + a.dx) / 2, (prev.dy + a.dy) / 2);
      }
      path.quadraticBezierTo(a.dx, a.dy, mid.dx, mid.dy);
    }
    return path..close();
  }

  @override
  bool shouldRepaint(_WashPainter old) =>
      old.seed != seed ||
      old.strength != strength ||
      old.ground != ground ||
      old.colors != colors;
}

/// Nurtura's mark: a sprout rising from a hill, under a mustard sun. The
/// same drawing is the app icon.
class VillageMark extends StatelessWidget {
  const VillageMark({super.key, this.size = 72});

  final double size;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return SizedBox.square(
      dimension: size,
      child: CustomPaint(
        painter: _MarkPainter(
          hill: p.primary,
          leaf: p.sage,
          sun: p.mustard,
          ground: p.primarySoft,
        ),
      ),
    );
  }
}

class _MarkPainter extends CustomPainter {
  _MarkPainter({
    required this.hill,
    required this.leaf,
    required this.sun,
    required this.ground,
  });

  final Color hill;
  final Color leaf;
  final Color sun;
  final Color ground;

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.width;
    // Soft round ground.
    canvas.drawCircle(Offset(s / 2, s / 2), s / 2, Paint()..color = ground);
    canvas.save();
    canvas.clipPath(
      Path()
        ..addOval(Rect.fromCircle(center: Offset(s / 2, s / 2), radius: s / 2)),
    );
    // Sun.
    canvas.drawCircle(Offset(s * 0.7, s * 0.3), s * 0.11, Paint()..color = sun);
    // Hill.
    canvas.drawPath(
      Path()
        ..moveTo(0, s * 0.78)
        ..quadraticBezierTo(s * 0.5, s * 0.52, s, s * 0.78)
        ..lineTo(s, s)
        ..lineTo(0, s)
        ..close(),
      Paint()..color = hill,
    );
    // Stem.
    canvas.drawPath(
      Path()
        ..moveTo(s * 0.5, s * 0.66)
        ..quadraticBezierTo(s * 0.49, s * 0.5, s * 0.5, s * 0.4),
      Paint()
        ..color = leaf
        ..style = PaintingStyle.stroke
        ..strokeWidth = s * 0.045
        ..strokeCap = StrokeCap.round,
    );
    // Two leaves.
    final leafPaint = Paint()..color = leaf;
    canvas.drawPath(
      Path()
        ..moveTo(s * 0.5, s * 0.47)
        ..quadraticBezierTo(s * 0.3, s * 0.46, s * 0.26, s * 0.3)
        ..quadraticBezierTo(s * 0.45, s * 0.3, s * 0.5, s * 0.47)
        ..close(),
      leafPaint,
    );
    canvas.drawPath(
      Path()
        ..moveTo(s * 0.5, s * 0.42)
        ..quadraticBezierTo(s * 0.58, s * 0.24, s * 0.76, s * 0.22)
        ..quadraticBezierTo(s * 0.72, s * 0.4, s * 0.5, s * 0.42)
        ..close(),
      leafPaint,
    );
    canvas.restore();
  }

  @override
  bool shouldRepaint(_MarkPainter old) =>
      old.hill != hill ||
      old.leaf != leaf ||
      old.sun != sun ||
      old.ground != ground;
}
