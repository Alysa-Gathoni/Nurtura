import '../models/explore_activity.dart';
import '../models/recommendation.dart';
import 'api_client.dart';

/// Explore: browse, search, save and try activities (#194).
class ExploreService {
  ExploreService(this._api);

  /// Searching loads the AI model on the server the first time.
  static const searchTimeout = Duration(seconds: 45);

  final ApiClient _api;

  /// Activities for the child, best first. [query] searches by meaning;
  /// [forInterests] searches with the child's interests.
  Future<List<ExploreActivity>> list(
    int childId, {
    String query = '',
    bool forInterests = false,
    String? area,
    bool noMaterials = false,
    bool quick = false,
    bool savedOnly = false,
    int limit = 30,
  }) async {
    final body = await _api.get(
      '/api/children/$childId/activities/',
      query: {
        if (query.trim().isNotEmpty) 'q': query.trim(),
        if (forInterests) 'for': 'interests',
        'area': ?area,
        if (noMaterials) 'no_materials': '1',
        if (quick) 'quick': '1',
        if (savedOnly) 'saved': '1',
        'limit': '$limit',
      },
      timeout: searchTimeout,
    ) as Map<String, dynamic>;
    return [
      for (final r in body['results'] as List? ?? const [])
        ExploreActivity.fromJson(r as Map<String, dynamic>),
    ];
  }

  Future<void> save(int childId, String activityId) =>
      _api.put('/api/children/$childId/saved/$activityId/', null);

  Future<void> unsave(int childId, String activityId) =>
      _api.delete('/api/children/$childId/saved/$activityId/');

  /// Adds the activity to the child's ideas, pinned first; returns the new
  /// batch.
  Future<RecommendationBatch> tryActivity(
    int childId,
    String activityId,
  ) async => RecommendationBatch.fromJson(
    await _api.post(
      '/api/children/$childId/activities/$activityId/try/',
      null,
      searchTimeout,
    ) as Map<String, dynamic>,
  );
}
