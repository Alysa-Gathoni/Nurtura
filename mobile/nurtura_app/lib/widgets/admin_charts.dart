import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../utils/dates.dart';

/// Chart colours for the admin dashboard (#123). The three trend colours,
/// and the outcome and milestone colours, were checked for colour-blind
/// separation and contrast in both themes (#116, #120).
class ChartColors {
  const ChartColors._({
    required this.ideas,
    required this.milestones,
    required this.feedback,
    required this.done,
    required this.partly,
    required this.notYet,
    required this.grid,
  });

  factory ChartColors.of(BuildContext context) {
    final p = context.palette;
    return Theme.of(context).brightness == Brightness.dark
        ? ChartColors._(
            ideas: const Color(0xFFD6744C),
            milestones: const Color(0xFF5A98DA),
            feedback: const Color(0xFF3F9F73),
            done: const Color(0xFF3E9E7C),
            partly: const Color(0xFFBB8418),
            notYet: const Color(0xFFD4566E),
            grid: p.border,
          )
        : ChartColors._(
            ideas: const Color(0xFFB4583A),
            milestones: const Color(0xFF2F73B8),
            feedback: const Color(0xFF4F8A3F),
            done: const Color(0xFF5A8C4C),
            partly: const Color(0xFFCF9B33),
            notYet: const Color(0xFFBC5F55),
            grid: p.border,
          );
  }

  final Color ideas, milestones, feedback, done, partly, notYet, grid;

  Color series(String key) => switch (key) {
    'ideas' => ideas,
    'milestones' => milestones,
    _ => feedback,
  };
}

const trendSeries = [
  ('ideas', 'Ideas generated'),
  ('milestones', 'Milestones recorded'),
  ('feedback', 'Feedback received'),
];

/// A round axis top at or above [value] (at least 4), divisible by 4.
int niceMax(int value) {
  final v = math.max(value, 4);
  final magnitude = math.pow(10, (math.log(v) / math.ln10).floor()).toInt();
  for (final step in [1, 2, 4, 5, 8, 10]) {
    final top = step * magnitude;
    if (top >= v && top % 4 == 0) return top;
  }
  return ((v + 3) ~/ 4) * 4;
}

/// Ideas, milestones and feedback per day, with a legend and a crosshair
/// that follows the finger.
class TrendChart extends StatefulWidget {
  const TrendChart({super.key, required this.dates, required this.series});

  final List<DateTime> dates;
  final Map<String, List<int>> series;

  @override
  State<TrendChart> createState() => _TrendChartState();
}

class _TrendChartState extends State<TrendChart> {
  int? _selected;

  static const _leftPad = 28.0, _bottomPad = 20.0, _height = 180.0;

  void _pick(Offset local, double width) {
    final n = widget.dates.length;
    if (n < 2) return;
    final plot = width - _leftPad;
    final i = (((local.dx - _leftPad) / plot) * (n - 1)).round().clamp(
      0,
      n - 1,
    );
    if (i != _selected) setState(() => _selected = i);
  }

  @override
  Widget build(BuildContext context) {
    final colors = ChartColors.of(context);
    final p = context.palette;
    final top = niceMax(
      trendSeries
          .map((s) => (widget.series[s.$1] ?? const []).fold(0, math.max))
          .fold(0, math.max),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Wrap(
          spacing: 14,
          runSpacing: 4,
          children: [
            for (final (key, label) in trendSeries)
              _LegendItem(
                color: colors.series(key),
                label: label,
                value: (widget.series[key] ?? const []).fold(
                  0,
                  (a, b) => a + b,
                ),
              ),
          ],
        ),
        const SizedBox(height: 8),
        LayoutBuilder(
          builder: (context, box) {
            final i = _selected;
            return GestureDetector(
              key: const Key('trendChart'),
              behavior: HitTestBehavior.opaque,
              onTapDown: (d) => _pick(d.localPosition, box.maxWidth),
              onHorizontalDragUpdate: (d) =>
                  _pick(d.localPosition, box.maxWidth),
              onHorizontalDragEnd: (_) => setState(() => _selected = null),
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  CustomPaint(
                    size: Size(box.maxWidth, _height),
                    painter: _TrendPainter(
                      dates: widget.dates,
                      series: widget.series,
                      colors: colors,
                      top: top,
                      selected: i,
                      textColor: p.mutedText,
                      leftPad: _leftPad,
                      bottomPad: _bottomPad,
                    ),
                  ),
                  if (i != null)
                    Positioned(
                      top: 0,
                      left: _tipLeft(i, box.maxWidth),
                      child: _Tooltip(
                        date: widget.dates[i],
                        values: {
                          for (final (key, _) in trendSeries)
                            key: widget.series[key]![i],
                        },
                        colors: colors,
                      ),
                    ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }

  double _tipLeft(int i, double width) {
    final n = widget.dates.length;
    final x = _leftPad + (width - _leftPad) * i / math.max(n - 1, 1);
    const tipWidth = 170.0;
    return x + 12 + tipWidth > width ? x - 12 - tipWidth : x + 12;
  }
}

class _TrendPainter extends CustomPainter {
  _TrendPainter({
    required this.dates,
    required this.series,
    required this.colors,
    required this.top,
    required this.selected,
    required this.textColor,
    required this.leftPad,
    required this.bottomPad,
  });

  final List<DateTime> dates;
  final Map<String, List<int>> series;
  final ChartColors colors;
  final int top;
  final int? selected;
  final Color textColor;
  final double leftPad, bottomPad;

  @override
  void paint(Canvas canvas, Size size) {
    final n = dates.length;
    final plotH = size.height - bottomPad - 6;
    double x(int i) =>
        leftPad + (size.width - leftPad) * i / math.max(n - 1, 1);
    double y(num v) => 6 + plotH * (1 - v / top);

    final grid = Paint()
      ..color = colors.grid
      ..strokeWidth = 1;
    for (var t = 0; t <= 4; t++) {
      final value = top * t / 4;
      final gy = y(value);
      canvas.drawLine(Offset(leftPad, gy), Offset(size.width, gy), grid);
      _text(
        canvas,
        value.round().toString(),
        Offset(leftPad - 6, gy),
        right: true,
      );
    }
    final every = math.max(1, n ~/ 5);
    for (var i = 0; i < n; i++) {
      if (i % every == 0 || i == n - 1) {
        _text(
          canvas,
          formatShortDate(dates[i]),
          Offset(x(i), size.height - 4),
          centre: true,
        );
      }
    }

    if (selected != null) {
      canvas.drawLine(
        Offset(x(selected!), 6),
        Offset(x(selected!), 6 + plotH),
        Paint()
          ..color = textColor
          ..strokeWidth = 1,
      );
    }

    for (final (key, _) in trendSeries) {
      final values = series[key] ?? const [];
      if (values.isEmpty) continue;
      final path = Path()..moveTo(x(0), y(values[0]));
      for (var i = 1; i < values.length; i++) {
        path.lineTo(x(i), y(values[i]));
      }
      final colour = colors.series(key);
      canvas.drawPath(
        path,
        Paint()
          ..color = colour
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2
          ..strokeJoin = StrokeJoin.round
          ..strokeCap = StrokeCap.round,
      );
      final dot = selected ?? values.length - 1;
      canvas.drawCircle(
        Offset(x(dot), y(values[dot])),
        4,
        Paint()..color = colour,
      );
    }
  }

  void _text(
    Canvas canvas,
    String text,
    Offset at, {
    bool right = false,
    bool centre = false,
  }) {
    final tp = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(color: textColor, fontSize: 10),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    final dx = right
        ? at.dx - tp.width
        : (centre ? at.dx - tp.width / 2 : at.dx);
    tp.paint(canvas, Offset(dx, at.dy - tp.height / 2 - (centre ? 4 : 0)));
  }

  @override
  bool shouldRepaint(_TrendPainter old) =>
      old.selected != selected ||
      old.series != series ||
      old.top != top ||
      old.colors != colors;
}

class _Tooltip extends StatelessWidget {
  const _Tooltip({
    required this.date,
    required this.values,
    required this.colors,
  });

  final DateTime date;
  final Map<String, int> values;
  final ChartColors colors;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Container(
      key: const Key('trendTooltip'),
      width: 170,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: p.card,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: p.border),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.12),
            blurRadius: 12,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            formatDate(date),
            style: AppText.nunito(size: 12, weight: FontWeight.w800),
          ),
          const SizedBox(height: 4),
          for (final (key, label) in trendSeries)
            Padding(
              padding: const EdgeInsets.only(top: 2),
              child: Row(
                children: [
                  _Swatch(colors.series(key)),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(label, style: AppText.nunito(size: 11.5)),
                  ),
                  Text(
                    '${values[key]}',
                    style: AppText.nunito(size: 12, weight: FontWeight.w800),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _LegendItem extends StatelessWidget {
  const _LegendItem({
    required this.color,
    required this.label,
    required this.value,
  });

  final Color color;
  final String label;
  final int value;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      _Swatch(color),
      const SizedBox(width: 6),
      Text(label, style: AppText.nunito(size: 12.5)),
      const SizedBox(width: 4),
      Text(
        '$value',
        style: AppText.nunito(size: 12.5, weight: FontWeight.w800),
      ),
    ],
  );
}

class _Swatch extends StatelessWidget {
  const _Swatch(this.color);

  final Color color;

  @override
  Widget build(BuildContext context) => Container(
    width: 10,
    height: 10,
    decoration: BoxDecoration(
      color: color,
      borderRadius: BorderRadius.circular(3),
    ),
  );
}

/// The legend swatch, for other widgets on the dashboard.
Widget chartSwatch(Color color) => _Swatch(color);

/// A small white trend line for the gradient summary cards.
class Sparkline extends StatelessWidget {
  const Sparkline(this.values, {super.key, this.width = 96, this.height = 32});

  final List<int> values;
  final double width, height;

  @override
  Widget build(BuildContext context) =>
      CustomPaint(size: Size(width, height), painter: _SparkPainter(values));
}

class _SparkPainter extends CustomPainter {
  _SparkPainter(this.values);

  final List<int> values;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.length < 2) return;
    final top = math.max(values.fold(0, math.max), 1);
    final path = Path();
    for (var i = 0; i < values.length; i++) {
      final x = size.width * i / (values.length - 1);
      final y = size.height - 3 - (size.height - 6) * values[i] / top;
      i == 0 ? path.moveTo(x, y) : path.lineTo(x, y);
    }
    canvas.drawPath(
      path,
      Paint()
        ..color = Colors.white.withValues(alpha: 0.92)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2
        ..strokeJoin = StrokeJoin.round
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(_SparkPainter old) => old.values != values;
}

/// Parts of a whole as a ring, with a label in the middle.
class DonutChart extends StatelessWidget {
  const DonutChart({
    super.key,
    required this.parts,
    required this.centre,
    required this.caption,
    this.size = 150,
  });

  final List<({int value, Color color})> parts;
  final String centre, caption;
  final double size;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return SizedBox.square(
      dimension: size,
      child: CustomPaint(
        painter: _DonutPainter(parts, p.cardAlt),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                centre,
                style: AppText.nunito(
                  size: 26,
                  weight: FontWeight.w800,
                  color: p.ink,
                ),
              ),
              Text(
                caption,
                style: AppText.nunito(size: 12, color: p.mutedText),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DonutPainter extends CustomPainter {
  _DonutPainter(this.parts, this.track);

  final List<({int value, Color color})> parts;
  final Color track;

  @override
  void paint(Canvas canvas, Size size) {
    const stroke = 16.0;
    final rect = Offset.zero & size;
    final arcRect = rect.deflate(stroke / 2);
    canvas.drawArc(
      arcRect,
      0,
      2 * math.pi,
      false,
      Paint()
        ..color = track
        ..style = PaintingStyle.stroke
        ..strokeWidth = stroke,
    );
    final total = parts.fold(0, (a, b) => a + b.value);
    if (total == 0) return;
    final visible = parts.where((p) => p.value > 0).length;
    final gap = visible > 1 ? 0.04 : 0.0;
    var start = -math.pi / 2;
    for (final part in parts) {
      if (part.value == 0) continue;
      final sweep = 2 * math.pi * part.value / total;
      canvas.drawArc(
        arcRect,
        start + gap / 2,
        math.max(sweep - gap, 0.001),
        false,
        Paint()
          ..color = part.color
          ..style = PaintingStyle.stroke
          ..strokeWidth = stroke,
      );
      start += sweep;
    }
  }

  @override
  bool shouldRepaint(_DonutPainter old) =>
      old.parts != parts || old.track != track;
}
