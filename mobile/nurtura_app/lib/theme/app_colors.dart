import 'package:flutter/material.dart';

/// Nurtura colour tokens. Widgets use these instead of hex values.
abstract final class AppColors {
  /// Primary buttons, active states, headings.
  static const tealDeep = Color(0xFF0D7D74);

  /// App bars, primary accents.
  static const teal = Color(0xFF14B8A6);

  /// Gradient accents.
  static const tealLight = Color(0xFF5EEAD4);

  /// Light backgrounds, secondary buttons, success pills.
  static const mint = Color(0xFFCFFAF0);

  /// Warm accent and a domain tag colour.
  static const coral = Color(0xFFFF8A5B);
  static const coralSoft = Color(0xFFFFE4D6);

  /// Highlights, stat icons, star ratings.
  static const gold = Color(0xFFFFC24B);

  /// Soft gold backgrounds, explanation boxes.
  static const goldSoft = Color(0xFFFFF2D6);

  /// Secondary tag colour.
  static const sky = Color(0xFF4FA6E8);
  static const skySoft = Color(0xFFDCEEFF);

  /// Primary text.
  static const ink = Color(0xFF1B2A28);

  /// Secondary and caption text.
  static const mutedText = Color(0xFF6E8582);

  /// Screen background.
  static const paper = Color(0xFFF4FBF9);
  static const card = Color(0xFFFFFFFF);
}
