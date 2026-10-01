import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';

/// Text styles: Nunito for UI text, Quicksand for headings and titles.
abstract final class AppText {
  /// Widget tests turn this off, since they can't download fonts.
  static bool useGoogleFonts = true;

  static TextStyle nunito({
    double size = 15,
    FontWeight weight = FontWeight.w500,
    Color color = AppColors.ink,
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
    Color color = AppColors.ink,
  }) {
    final style = TextStyle(fontSize: size, fontWeight: weight, color: color);
    return useGoogleFonts ? GoogleFonts.quicksand(textStyle: style) : style;
  }
}

abstract final class AppRadii {
  static const card = 18.0;
  static const button = 14.0;
  static const field = 12.0;
}

/// Soft, blurred shadows rather than hard drop shadows.
abstract final class AppShadows {
  static List<BoxShadow> card = [
    BoxShadow(
      color: AppColors.ink.withValues(alpha: 0.07),
      blurRadius: 18,
      offset: const Offset(0, 6),
    ),
  ];

  static List<BoxShadow> primaryButton = [
    BoxShadow(
      color: AppColors.teal.withValues(alpha: 0.35),
      blurRadius: 14,
      offset: const Offset(0, 6),
    ),
  ];
}

abstract final class AppTheme {
  static ThemeData light() {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: AppColors.teal,
      primary: AppColors.tealDeep,
      secondary: AppColors.coral,
      surface: AppColors.card,
      error: AppColors.coral,
    );
    OutlineInputBorder border(Color color) => OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.field),
          borderSide: BorderSide(color: color, width: 2),
        );

    return ThemeData(
      useMaterial3: true,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: AppColors.paper,
      textTheme: TextTheme(
        headlineMedium: AppText.quicksand(size: 30),
        headlineSmall: AppText.quicksand(size: 24),
        titleLarge: AppText.quicksand(size: 20),
        titleMedium: AppText.nunito(size: 16, weight: FontWeight.w800),
        bodyLarge: AppText.nunito(size: 16),
        bodyMedium: AppText.nunito(size: 14.5),
        bodySmall: AppText.nunito(size: 13, color: AppColors.mutedText),
        labelLarge: AppText.nunito(size: 15, weight: FontWeight.w800),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.card,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        hintStyle: AppText.nunito(color: AppColors.mutedText),
        errorStyle: AppText.nunito(
          size: 12.5,
          weight: FontWeight.w700,
          color: AppColors.coral,
        ),
        border: border(AppColors.mint),
        enabledBorder: border(AppColors.mint),
        focusedBorder: border(AppColors.teal),
        errorBorder: border(AppColors.coral),
        focusedErrorBorder: border(AppColors.coral),
      ),
      progressIndicatorTheme:
          const ProgressIndicatorThemeData(color: AppColors.tealDeep),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: AppColors.ink,
        contentTextStyle: AppText.nunito(color: Colors.white),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadii.button),
        ),
      ),
    );
  }
}
