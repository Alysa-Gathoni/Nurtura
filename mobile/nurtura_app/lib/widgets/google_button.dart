import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// "Continue with Google" (#130), in Google's neutral button style: the
/// four-colour G on white (or near-black in dark mode) with a grey outline.
class GoogleButton extends StatelessWidget {
  const GoogleButton({super.key, required this.onPressed});

  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final dark = Theme.of(context).brightness == Brightness.dark;
    return SizedBox(
      height: 52,
      child: OutlinedButton(
        onPressed: onPressed,
        style: OutlinedButton.styleFrom(
          backgroundColor: dark ? const Color(0xFF131314) : Colors.white,
          foregroundColor: dark
              ? const Color(0xFFE3E3E3)
              : const Color(0xFF1F1F1F),
          side: BorderSide(
            color: dark ? const Color(0xFF8E918F) : const Color(0xFF747775),
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadii.button),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox.square(
              dimension: 20,
              child: CustomPaint(painter: _GoogleG()),
            ),
            const SizedBox(width: 12),
            Flexible(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: Text(
                  'Continue with Google',
                  style: AppText.nunito(size: 15.5, weight: FontWeight.w800),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Google's G: blue, green, yellow and red arcs and the blue bar.
class _GoogleG extends CustomPainter {
  const _GoogleG();

  static const _blue = Color(0xFF4285F4);
  static const _green = Color(0xFF34A853);
  static const _yellow = Color(0xFFFBBC05);
  static const _red = Color(0xFFEA4335);

  @override
  void paint(Canvas canvas, Size size) {
    final s = size.shortestSide;
    final stroke = s * 0.2;
    final rect = Rect.fromCircle(
      center: Offset(s / 2, s / 2),
      radius: (s - stroke) / 2,
    );
    double deg(double d) => d * math.pi / 180;
    Paint pen(Color c) => Paint()
      ..color = c
      ..style = PaintingStyle.stroke
      ..strokeWidth = stroke;
    // Clockwise from the right, leaving the G's opening at the top right.
    canvas
      ..drawArc(rect, deg(0), deg(45), false, pen(_blue))
      ..drawArc(rect, deg(45), deg(90), false, pen(_green))
      ..drawArc(rect, deg(135), deg(80), false, pen(_yellow))
      ..drawArc(rect, deg(215), deg(100), false, pen(_red))
      ..drawRect(
        Rect.fromLTWH(s / 2, s / 2 - stroke / 2, s / 2, stroke),
        Paint()..color = _blue,
      );
  }

  @override
  bool shouldRepaint(_GoogleG oldDelegate) => false;
}
