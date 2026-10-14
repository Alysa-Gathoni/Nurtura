import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/recommendation.dart';

/// The last recommendation batch per child, kept on the device so it can
/// be shown offline (NFR-14). Cleared whenever the user signs out or the
/// session ends, so another account on the same phone never sees it.
abstract class RecommendationCache {
  Future<CachedBatch?> read(int childId);
  Future<void> write(int childId, RecommendationBatch batch);
  Future<void> clear();
}

/// A cached batch and when it was saved on this device.
class CachedBatch {
  const CachedBatch(this.batch, this.savedAt);

  final RecommendationBatch batch;
  final DateTime savedAt;
}

/// [RecommendationCache] in the app's shared preferences.
class SharedPrefsRecommendationCache implements RecommendationCache {
  static const _prefix = 'nurtura.recommendations.child.';

  Future<SharedPreferences> get _prefs => SharedPreferences.getInstance();

  @override
  Future<CachedBatch?> read(int childId) async {
    final raw = (await _prefs).getString('$_prefix$childId');
    if (raw == null) return null;
    try {
      final data = jsonDecode(raw) as Map<String, dynamic>;
      return CachedBatch(
        RecommendationBatch.fromJson(data['batch'] as Map<String, dynamic>),
        DateTime.parse(data['saved_at'] as String),
      );
    } on Object {
      return null; // unreadable (e.g. an older format): treat as not cached
    }
  }

  @override
  Future<void> write(int childId, RecommendationBatch batch) async {
    await (await _prefs).setString(
      '$_prefix$childId',
      jsonEncode({
        'saved_at': DateTime.now().toIso8601String(),
        'batch': batch.toJson(),
      }),
    );
  }

  @override
  Future<void> clear() async {
    final prefs = await _prefs;
    for (final key in prefs.getKeys().where((k) => k.startsWith(_prefix))) {
      await prefs.remove(key);
    }
  }
}

/// In-memory cache for tests.
class MemoryRecommendationCache implements RecommendationCache {
  final entries = <int, CachedBatch>{};

  @override
  Future<CachedBatch?> read(int childId) async => entries[childId];

  @override
  Future<void> write(int childId, RecommendationBatch batch) async =>
      entries[childId] = CachedBatch(batch, DateTime.now());

  @override
  Future<void> clear() async => entries.clear();
}
