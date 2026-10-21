import '../models/admin.dart';
import 'api_client.dart';

/// The administrator API (`/api/admin/`, #122).
class AdminService {
  AdminService(this._api);

  /// Updating the search index loads the AI model on the server the first
  /// time, which can take about 15 seconds.
  static const searchIndexTimeout = Duration(seconds: 60);

  final ApiClient _api;

  Future<AdminOverview> overview({int days = 30}) async =>
      AdminOverview.fromJson(
        await _api.get('/api/admin/overview/', query: {'range': '$days'})
            as Map<String, dynamic>,
      );

  Future<List<AdminActivity>> activities({
    String? status,
    String? domain,
    String search = '',
  }) async {
    final rows = await _api.get(
      '/api/admin/activities/',
      query: {
        'status': ?status,
        'domain': ?domain,
        if (search.trim().isNotEmpty) 'search': search.trim(),
      },
    ) as List;
    return [
      for (final r in rows) AdminActivity.fromJson(r as Map<String, dynamic>),
    ];
  }

  Future<AdminActivity> activity(int id) async => AdminActivity.fromJson(
    await _api.get('/api/admin/activities/$id/') as Map<String, dynamic>,
  );

  /// Adds an activity; it starts as Draft.
  Future<AdminActivity> create(Map<String, String> fields) async =>
      AdminActivity.fromJson(
        await _api.post('/api/admin/activities/', fields)
            as Map<String, dynamic>,
      );

  /// Saves edits; reviewed content goes back to Draft on the server.
  Future<AdminActivity> update(int id, Map<String, String> fields) async =>
      AdminActivity.fromJson(
        await _api.patch('/api/admin/activities/$id/', fields)
            as Map<String, dynamic>,
      );

  Future<AdminActivity> setStatus(int id, String status) async =>
      AdminActivity.fromJson(
        await _api.post('/api/admin/activities/$id/status/', {'status': status})
            as Map<String, dynamic>,
      );

  Future<AdminChoices> choices() async => AdminChoices.fromJson(
    await _api.get('/api/admin/choices/') as Map<String, dynamic>,
  );

  Future<({int count, List<AdminFeedback> items})> feedback({
    int? rating,
    String? domain,
    int? activity,
    int limit = 50,
    int offset = 0,
  }) async {
    final json = await _api.get(
      '/api/admin/feedback/',
      query: {
        if (rating != null) 'rating': '$rating',
        'domain': ?domain,
        if (activity != null) 'activity': '$activity',
        'limit': '$limit',
        'offset': '$offset',
      },
    ) as Map<String, dynamic>;
    return (
      count: (json['count'] as num).toInt(),
      items: [
        for (final r in json['results'] as List)
          AdminFeedback.fromJson(r as Map<String, dynamic>),
      ],
    );
  }

  /// Makes Published activities searchable; returns the server's summary.
  Future<String> updateSearchIndex() async {
    final json = await _api.post(
      '/api/admin/search-index/',
      null,
      searchIndexTimeout,
    ) as Map<String, dynamic>;
    return json['message'] as String? ?? '';
  }
}
