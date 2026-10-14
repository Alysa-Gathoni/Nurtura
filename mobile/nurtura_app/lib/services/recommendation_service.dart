import '../models/recommendation.dart';
import 'api_client.dart';

/// A child's ranked recommendations (`/api/children/<id>/recommendations/`).
class RecommendationService {
  RecommendationService(this._api);

  /// Generating can take ~16 s on a server's first request (the AI model
  /// loads), so allow well over that before giving up.
  static const generateTimeout = Duration(seconds: 45);

  final ApiClient _api;

  String _path(int childId) => '/api/children/$childId/recommendations/';

  /// The newest stored batch; never generates.
  Future<RecommendationBatch> latest(int childId) async =>
      RecommendationBatch.fromJson(
        await _api.get(_path(childId)) as Map<String, dynamic>,
      );

  /// Generates (201) or returns the identical newest batch (200); both are
  /// handled the same way.
  Future<RecommendationBatch> generate(int childId) async =>
      RecommendationBatch.fromJson(
        await _api.post(_path(childId), null, generateTimeout)
            as Map<String, dynamic>,
      );

  /// Marks the activity done, or partly done (FR-14).
  Future<Completion> markDone(
    int recommendationId, {
    bool partial = false,
  }) async => Completion.fromJson(
    await _api.put('/api/recommendations/$recommendationId/completion/', {
      'status': partial ? 'partially_completed' : 'completed',
    }) as Map<String, dynamic>,
  );

  /// Undoes a mistaken "done".
  Future<void> undoDone(int recommendationId) =>
      _api.delete('/api/recommendations/$recommendationId/completion/');

  /// Records or replaces the caregiver's feedback (FR-15).
  Future<ActivityFeedback> sendFeedback(
    int recommendationId, {
    required int rating,
    String comment = '',
  }) async => ActivityFeedback.fromJson(
    await _api.put('/api/recommendations/$recommendationId/feedback/', {
      'rating': rating,
      'comment': comment.trim(),
    }) as Map<String, dynamic>,
  );

  /// The newest batch, generating one first if there isn't any yet.
  Future<RecommendationBatch> load(
    int childId, {
    void Function()? onGenerating,
  }) async {
    final stored = await latest(childId);
    if (!stored.isEmpty) return stored;
    onGenerating?.call();
    return generate(childId);
  }
}
