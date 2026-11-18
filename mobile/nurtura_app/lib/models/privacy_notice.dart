/// The privacy notice caregivers agree to (#136), as the server sends it.
class PrivacyNotice {
  const PrivacyNotice({
    required this.version,
    required this.title,
    required this.sections,
    this.summary = const [],
  });

  factory PrivacyNotice.fromJson(Map<String, dynamic> json) => PrivacyNotice(
    version: json['version'] as String,
    title: json['title'] as String,
    summary: [
      for (final point in json['summary'] as List? ?? const []) point as String,
    ],
    sections: [
      for (final s in json['sections'] as List)
        (
          heading: (s as Map<String, dynamic>)['heading'] as String,
          body: s['body'] as String,
        ),
    ],
  );

  /// Sent back when agreeing, so only the wording shown can be agreed to.
  final String version;
  final String title;
  final List<({String heading, String body})> sections;

  /// The notice in short, shown first before agreeing (#238). Empty from a
  /// backend older than #238, in which case the full notice is shown.
  final List<String> summary;
}
