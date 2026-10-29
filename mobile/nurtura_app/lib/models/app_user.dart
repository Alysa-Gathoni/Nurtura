class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.role,
    this.privacyConsentRequired = false,
    this.hasPassword = true,
  });

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
    id: json['id'] as int,
    email: (json['email'] as String?) ?? '',
    role: (json['role'] as String?) ?? '',
    privacyConsentRequired: json['privacy_consent_required'] == true,
    hasPassword: json['has_password'] != false,
  );

  static const administratorRole = 'administrator';

  final int id;
  final String email;
  final String role;

  /// The privacy notice must be agreed before anything else (#136).
  final bool privacyConsentRequired;

  /// False for an account made with Google, which has no password until
  /// one is set with an emailed code (#142).
  final bool hasPassword;

  bool get isAdministrator => role == administratorRole;
}
