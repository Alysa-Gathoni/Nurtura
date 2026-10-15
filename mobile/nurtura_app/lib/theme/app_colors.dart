import 'package:flutter/material.dart';

/// Nurtura's "village" colours: warm earth tones on linen cream. Widgets read
/// colours from the theme through `context.palette`, so they follow light
/// and dark mode; these constants are the light palette's source.
abstract final class AppColors {
  /// Terracotta: actions, selected states, headings that need weight.
  static const terracotta = Color(0xFFB4583A);

  /// Sage: things done, growing or going well.
  static const sage = Color(0xFF6A8763);

  /// Mustard: streaks, badges and the "why this" notes.
  static const mustard = Color(0xFFCF9B33);

  /// Warm brown text on linen.
  static const ink = Color(0xFF3B2F28);
  static const mutedText = Color(0xFF85766A);

  /// Linen cream background and the paper-white of cards.
  static const linen = Color(0xFFF7F0E3);
  static const card = Color(0xFFFFFBF3);
}

/// The colours for one brightness. Read with `context.palette`.
@immutable
class NurturaPalette extends ThemeExtension<NurturaPalette> {
  const NurturaPalette({
    required this.primary,
    required this.primaryMid,
    required this.primaryLight,
    required this.primarySoft,
    required this.onPrimary,
    required this.sage,
    required this.sageSoft,
    required this.mustard,
    required this.mustardSoft,
    required this.dusk,
    required this.duskSoft,
    required this.rose,
    required this.roseSoft,
    required this.plum,
    required this.plumSoft,
    required this.ink,
    required this.mutedText,
    required this.paper,
    required this.card,
    required this.cardAlt,
    required this.border,
  });

  /// Terracotta: primary buttons, selected states, links.
  final Color primary;
  final Color primaryMid;
  final Color primaryLight;

  /// Terracotta wash: secondary buttons, selected backgrounds.
  final Color primarySoft;

  /// Text and icons on [primary].
  final Color onPrimary;

  /// Sage: done, celebrated, growing.
  final Color sage;
  final Color sageSoft;

  /// Mustard: streaks, badges, "why this" notes.
  final Color mustard;
  final Color mustardSoft;

  /// Dusty blue (Talking), rose (Feelings, errors) and plum (Senses).
  final Color dusk;
  final Color duskSoft;
  final Color rose;
  final Color roseSoft;
  final Color plum;
  final Color plumSoft;

  /// Main and secondary text.
  final Color ink;
  final Color mutedText;

  /// Linen background, cards, a slightly deeper card, and hairlines.
  final Color paper;
  final Color card;
  final Color cardAlt;
  final Color border;

  static const light = NurturaPalette(
    primary: AppColors.terracotta,
    primaryMid: Color(0xFFC9714F),
    primaryLight: Color(0xFFE2A285),
    primarySoft: Color(0xFFF4DFD2),
    onPrimary: Color(0xFFFFF8EF),
    sage: AppColors.sage,
    sageSoft: Color(0xFFE2E9D7),
    mustard: AppColors.mustard,
    mustardSoft: Color(0xFFF6EACB),
    dusk: Color(0xFF5B7E92),
    duskSoft: Color(0xFFDDE7EB),
    rose: Color(0xFFBC5F55),
    roseSoft: Color(0xFFF5DDD8),
    plum: Color(0xFF876C8F),
    plumSoft: Color(0xFFEBE1EC),
    ink: AppColors.ink,
    mutedText: AppColors.mutedText,
    paper: AppColors.linen,
    card: AppColors.card,
    cardAlt: Color(0xFFF1E6D3),
    border: Color(0xFFE6D7BF),
  );

  /// Evening by the fire: warm browns instead of blue-black.
  static const dark = NurturaPalette(
    primary: Color(0xFFE38D69),
    primaryMid: Color(0xFFC9714F),
    primaryLight: Color(0xFF8A4A33),
    primarySoft: Color(0xFF47291D),
    onPrimary: Color(0xFF2A140B),
    sage: Color(0xFFA1BC97),
    sageSoft: Color(0xFF2C3627),
    mustard: Color(0xFFE6BD63),
    mustardSoft: Color(0xFF3D3120),
    dusk: Color(0xFF97B5C6),
    duskSoft: Color(0xFF243139),
    rose: Color(0xFFE59B8F),
    roseSoft: Color(0xFF452722),
    plum: Color(0xFFC6A8CD),
    plumSoft: Color(0xFF382C3B),
    ink: Color(0xFFF3EADC),
    mutedText: Color(0xFFB6A796),
    paper: Color(0xFF1E1915),
    card: Color(0xFF28211C),
    cardAlt: Color(0xFF332A23),
    border: Color(0xFF44382E),
  );

  @override
  NurturaPalette copyWith() => this;

  @override
  NurturaPalette lerp(NurturaPalette? other, double t) {
    if (other == null) return this;
    Color mix(Color a, Color b) => Color.lerp(a, b, t)!;
    return NurturaPalette(
      primary: mix(primary, other.primary),
      primaryMid: mix(primaryMid, other.primaryMid),
      primaryLight: mix(primaryLight, other.primaryLight),
      primarySoft: mix(primarySoft, other.primarySoft),
      onPrimary: mix(onPrimary, other.onPrimary),
      sage: mix(sage, other.sage),
      sageSoft: mix(sageSoft, other.sageSoft),
      mustard: mix(mustard, other.mustard),
      mustardSoft: mix(mustardSoft, other.mustardSoft),
      dusk: mix(dusk, other.dusk),
      duskSoft: mix(duskSoft, other.duskSoft),
      rose: mix(rose, other.rose),
      roseSoft: mix(roseSoft, other.roseSoft),
      plum: mix(plum, other.plum),
      plumSoft: mix(plumSoft, other.plumSoft),
      ink: mix(ink, other.ink),
      mutedText: mix(mutedText, other.mutedText),
      paper: mix(paper, other.paper),
      card: mix(card, other.card),
      cardAlt: mix(cardAlt, other.cardAlt),
      border: mix(border, other.border),
    );
  }
}

extension PaletteContext on BuildContext {
  /// The current theme's colours (light or dark).
  NurturaPalette get palette =>
      Theme.of(this).extension<NurturaPalette>() ?? NurturaPalette.light;
}
