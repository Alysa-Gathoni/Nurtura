import '../utils/dates.dart';

class ChildProfile {
  const ChildProfile({
    required this.id,
    required this.name,
    required this.dateOfBirth,
    this.interests = const [],
    this.concerns = const [],
  });

  factory ChildProfile.fromJson(Map<String, dynamic> json) => ChildProfile(
    id: json['id'] as int,
    name: json['name'] as String,
    dateOfBirth: DateTime.parse(json['date_of_birth'] as String),
    interests: List<String>.from(json['interests'] as List? ?? const []),
    concerns: List<String>.from(json['concerns'] as List? ?? const []),
  );

  final int id;
  final String name;

  /// Birth date, or the expected due date for an expecting parent.
  final DateTime dateOfBirth;
  final List<String> interests;
  final List<String> concerns;

  bool get isExpecting => dateOfBirth.isAfter(today());

  /// "14 months", or "Due 1 Feb 2027" for an expected baby.
  String get ageDescription =>
      isExpecting ? 'Due ${formatDate(dateOfBirth)}' : ageLabel(dateOfBirth);
}
