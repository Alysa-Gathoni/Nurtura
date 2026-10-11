import 'package:flutter/material.dart';

/// Nurtura's brand colours (light values). Widgets read colours from the
/// theme instead, through `context.palette`, so they follow light and dark
/// mode; these constants are the light palette's source.
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

  /// Highlights, streaks, badges.
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

/// The colours for one brightness. Read with `context.palette`.
@immutable
class NurturaPalette extends ThemeExtension<NurturaPalette> {
  const NurturaPalette({
    required this.tealDeep,
    required this.teal,
    required this.tealLight,
    required this.mint,
    required this.coral,
    required this.coralSoft,
    required this.gold,
    required this.goldSoft,
    required this.sky,
    required this.skySoft,
    required this.ink,
    required this.mutedText,
    required this.paper,
    required this.card,
    required this.cardAlt,
    required this.border,
    required this.onPrimary,
    required this.headerStart,
    required this.headerEnd,
  });

  /// Accent for headings, active states and primary buttons.
  final Color tealDeep;
  final Color teal;
  final Color tealLight;

  /// Soft accent background (secondary buttons, success).
  final Color mint;
  final Color coral;
  final Color coralSoft;
  final Color gold;
  final Color goldSoft;
  final Color sky;
  final Color skySoft;

  /// Main and secondary text.
  final Color ink;
  final Color mutedText;

  /// Screen background, cards, and a slightly raised card.
  final Color paper;
  final Color card;
  final Color cardAlt;
  final Color border;

  /// Text and icons on [tealDeep] (primary buttons, selected chips).
  final Color onPrimary;

  /// The header gradient.
  final Color headerStart;
  final Color headerEnd;

  static const light = NurturaPalette(
    tealDeep: AppColors.tealDeep,
    teal: AppColors.teal,
    tealLight: AppColors.tealLight,
    mint: AppColors.mint,
    coral: AppColors.coral,
    coralSoft: AppColors.coralSoft,
    gold: AppColors.gold,
    goldSoft: AppColors.goldSoft,
    sky: AppColors.sky,
    skySoft: AppColors.skySoft,
    ink: AppColors.ink,
    mutedText: AppColors.mutedText,
    paper: AppColors.paper,
    card: AppColors.card,
    cardAlt: Color(0xFFEAF7F3),
    border: Color(0xFFD6EFE9),
    onPrimary: Colors.white,
    headerStart: Color(0xFF0FA595),
    headerEnd: Color(0xFF14B8A6),
  );

  static const dark = NurturaPalette(
    tealDeep: Color(0xFF5EEAD4),
    teal: Color(0xFF14B8A6),
    tealLight: Color(0xFF2DD4BF),
    mint: Color(0xFF123F39),
    coral: Color(0xFFFF9B73),
    coralSoft: Color(0xFF41291F),
    gold: Color(0xFFFFC85C),
    goldSoft: Color(0xFF3A3020),
    sky: Color(0xFF72BDF2),
    skySoft: Color(0xFF1C3146),
    ink: Color(0xFFE7F3F0),
    mutedText: Color(0xFF97ADA9),
    paper: Color(0xFF0D1615),
    card: Color(0xFF162321),
    cardAlt: Color(0xFF1E2E2B),
    border: Color(0xFF29403C),
    onPrimary: Color(0xFF052B27),
    headerStart: Color(0xFF0B5F57),
    headerEnd: Color(0xFF0E7A70),
  );

  @override
  NurturaPalette copyWith() => this;

  @override
  NurturaPalette lerp(NurturaPalette? other, double t) {
    if (other == null) return this;
    Color mix(Color a, Color b) => Color.lerp(a, b, t)!;
    return NurturaPalette(
      tealDeep: mix(tealDeep, other.tealDeep),
      teal: mix(teal, other.teal),
      tealLight: mix(tealLight, other.tealLight),
      mint: mix(mint, other.mint),
      coral: mix(coral, other.coral),
      coralSoft: mix(coralSoft, other.coralSoft),
      gold: mix(gold, other.gold),
      goldSoft: mix(goldSoft, other.goldSoft),
      sky: mix(sky, other.sky),
      skySoft: mix(skySoft, other.skySoft),
      ink: mix(ink, other.ink),
      mutedText: mix(mutedText, other.mutedText),
      paper: mix(paper, other.paper),
      card: mix(card, other.card),
      cardAlt: mix(cardAlt, other.cardAlt),
      border: mix(border, other.border),
      onPrimary: mix(onPrimary, other.onPrimary),
      headerStart: mix(headerStart, other.headerStart),
      headerEnd: mix(headerEnd, other.headerEnd),
    );
  }
}

extension PaletteContext on BuildContext {
  /// The current theme's colours (light or dark).
  NurturaPalette get palette =>
      Theme.of(this).extension<NurturaPalette>() ?? NurturaPalette.light;
}
