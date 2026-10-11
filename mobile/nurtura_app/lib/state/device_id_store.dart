import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// A random ID for this phone, created once and kept across logouts, so the
/// server can trust the phone for 30 days after an emailed code (#91). The
/// server stores only a hash of it.
abstract class DeviceIdStore {
  Future<String> id();
}

String newDeviceId([Random? random]) {
  final r = random ?? Random.secure();
  return List.generate(32, (_) => r.nextInt(16).toRadixString(16)).join();
}

/// Kept in the Keychain / Keystore.
class SecureDeviceIdStore implements DeviceIdStore {
  static const _key = 'nurtura_device_id';
  final _storage = const FlutterSecureStorage();

  @override
  Future<String> id() async {
    final saved = await _storage.read(key: _key);
    if (saved != null && saved.length >= 16) return saved;
    final created = newDeviceId();
    await _storage.write(key: _key, value: created);
    return created;
  }
}

/// In-memory, for tests.
class MemoryDeviceIdStore implements DeviceIdStore {
  MemoryDeviceIdStore([String? id]) : _id = id ?? newDeviceId();

  final String _id;

  @override
  Future<String> id() async => _id;
}
