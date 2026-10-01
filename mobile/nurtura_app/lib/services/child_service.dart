import '../models/child_profile.dart';
import '../utils/dates.dart';
import 'api_client.dart';

/// The caregiver's child profiles (/api/children/).
class ChildService {
  ChildService(this._api);

  final ApiClient _api;

  Future<List<ChildProfile>> list() async {
    final data = await _api.get('/api/children/') as List;
    return data
        .map((e) => ChildProfile.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<ChildProfile> create({
    required String name,
    required DateTime dateOfBirth,
    List<String> interests = const [],
    List<String> concerns = const [],
  }) async {
    final data = await _api.post('/api/children/', {
      'name': name.trim(),
      'date_of_birth': apiDate(dateOfBirth),
      'interests': interests,
      'concerns': concerns,
    });
    return ChildProfile.fromJson(data as Map<String, dynamic>);
  }
}
