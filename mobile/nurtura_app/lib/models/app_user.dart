class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.role,
    this.privacyConsentRequired = false,
  });

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
    id: json['id'] as int,
    email: (json['email'] as String?) ?? '',
    role: (json['role'] as String?) ?? '',
    privacyConsentRequired: json['privacy_consent_required'] == true,
  );

  static const administratorRole = 'administrator';

  final int id;
  final String email;
  final String role;

  /// The privacy notice must be agreed before anything else (#136).
  final bool privacyConsentRequired;

  bool get isAdministrator => role == administratorRole;
}
