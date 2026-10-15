import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';

/// Text styles: Nunito for UI text, Quicksand for headings and titles.
///
/// With no [color], text takes the theme's text colour, so it reads well in
/// both light and dark mode.
abstract final class AppText {
  /// Widget tests turn this off, since they can't download fonts.
  static bool useGoogleFonts = true;

  static TextStyle nunito({
    double size = 15,
    FontWeight weight = FontWeight.w500,
    Color? color,
    double? height,
  }) {
    final style = TextStyle(
      fontSize: size,
      fontWeight: weight,
      color: color,
      height: height,
    );
    return useGoogleFonts ? GoogleFonts.nunito(textStyle: style) : style;
  }

  static TextStyle quicksand({
    double size = 22,
    FontWeight weight = FontWeight.w700,
    Color? color,
  }) {
    final style = TextStyle(fontSize: size, fontWeight: weight, color: color);
    return useGoogleFonts ? GoogleFonts.quicksand(textStyle: style) : style;
  }
}

abstract final class AppRadii {
  static const card = 20.0;

  /// Pill-shaped buttons.
  static const button = 26.0;
  static const field = 14.0;
}

/// A faint warm lift, like paper resting on linen; no glows.
abstract final class AppShadows {
  static List<BoxShadow> card = [
    BoxShadow(
      color: const Color(0xFF6B4A2F).withValues(alpha: 0.07),
      blurRadius: 10,
      offset: const Offset(0, 3),
    ),
  ];

  static const List<BoxShadow> primaryButton = [];
}

abstract final class AppTheme {
  static ThemeData light() => _build(NurturaPalette.light, Brightness.light);

  static ThemeData dark() => _build(NurturaPalette.dark, Brightness.dark);

  static ThemeData _build(NurturaPalette p, Brightness brightness) {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: AppColors.terracotta,
      brightness: brightness,
      primary: p.primary,
      onPrimary: p.onPrimary,
      secondary: p.sage,
      surface: p.card,
      onSurface: p.ink,
      error: p.rose,
    );
    OutlineInputBorder border(Color color) => OutlineInputBorder(
      borderRadius: BorderRadius.circular(AppRadii.field),
      borderSide: BorderSide(color: color, width: 2),
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: colorScheme,
      extensions: [p],
      scaffoldBackgroundColor: p.paper,
      textTheme: TextTheme(
        headlineMedium: AppText.quicksand(size: 30, color: p.ink),
        headlineSmall: AppText.quicksand(size: 24, color: p.ink),
        titleLarge: AppText.quicksand(size: 20, color: p.ink),
        titleMedium: AppText.nunito(
          size: 16,
          weight: FontWeight.w800,
          color: p.ink,
        ),
        bodyLarge: AppText.nunito(size: 16, color: p.ink),
        bodyMedium: AppText.nunito(size: 14.5, color: p.ink),
        bodySmall: AppText.nunito(size: 13, color: p.mutedText),
        labelLarge: AppText.nunito(
          size: 15,
          weight: FontWeight.w800,
          color: p.ink,
        ),
      ),
      iconTheme: IconThemeData(color: p.ink),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: p.card,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 14,
        ),
        hintStyle: AppText.nunito(color: p.mutedText),
        errorStyle: AppText.nunito(
          size: 12.5,
          weight: FontWeight.w700,
          color: p.rose,
        ),
        border: border(p.border),
        enabledBorder: border(p.border),
        focusedBorder: border(p.primary),
        errorBorder: border(p.rose),
        focusedErrorBorder: border(p.rose),
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(color: p.primary),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: p.card,
        surfaceTintColor: Colors.transparent,
        indicatorColor: p.primarySoft,
        height: 68,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (states) => AppText.nunito(
            size: 12,
            weight: FontWeight.w800,
            color: states.contains(WidgetState.selected)
                ? p.primary
                : p.mutedText,
          ),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            color: states.contains(WidgetState.selected)
                ? p.primary
                : p.mutedText,
          ),
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: p.card,
        showDragHandle: true,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        ),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith(
          (states) =>
              states.contains(WidgetState.selected) ? p.onPrimary : p.mutedText,
        ),
        trackColor: WidgetStateProperty.resolveWith(
          (states) =>
              states.contains(WidgetState.selected) ? p.primary : p.cardAlt,
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: p.ink,
        contentTextStyle: AppText.nunito(color: p.paper),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.button),
        ),
      ),
    );
  }
}
