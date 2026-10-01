class AppUser {
  const AppUser({required this.id, required this.email, required this.role});

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        id: json['id'] as int,
        email: (json['email'] as String?) ?? '',
        role: (json['role'] as String?) ?? '',
      );

  final int id;
  final String email;
  final String role;
}
