import '../models/reference_milestone.dart';
import 'api_client.dart';

/// The guideline milestone catalogue and milestone recording.
class MilestoneService {
  MilestoneService(this._api);

  final ApiClient _api;

  /// Catalogue milestones matching [search] (every word) and [domain].
  Future<List<ReferenceMilestone>> search({
    String search = '',
    String? domain,
  }) async {
    final data = await _api.get(
      '/api/reference-milestones/',
      query: {
        if (search.trim().isNotEmpty) 'search': search.trim(),
        'domain': ?domain,
      },
    ) as List;
    return data
        .map((e) => ReferenceMilestone.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Every observation recorded for the child (read-only).
  Future<List<MilestoneObservation>> history(int childId) async {
    final data = await _api.get('/api/children/$childId/milestones/') as List;
    return data
        .map((e) => MilestoneObservation.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Records an observation; the backend regenerates the child's profile.
  Future<RecordedMilestone> record({
    required int childId,
    required ReferenceMilestone milestone,
    required MilestoneStatus status,
  }) async {
    final data = await _api.post('/api/children/$childId/milestones/', {
      'reference': milestone.id,
      'status': status.apiValue,
    });
    return RecordedMilestone.fromJson(data as Map<String, dynamic>);
  }
}
