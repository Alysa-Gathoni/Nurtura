import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// The account this phone can log back in to with a fingerprint (#150).
class SavedFingerprint {
  const SavedFingerprint({required this.email, required this.key});

  final String email;

  /// The email partly hidden, "a***@example.com", for the login screen,
  /// which anyone holding the phone can see. Same rule as the backend's
  /// `two_factor.mask_email`.
  String get maskedEmail {
    final at = email.indexOf('@');
    if (at < 1) return 'your account';
    return '${email[0]}***${email.substring(at)}';
  }

  /// From the server; sent back only after the phone's fingerprint check.
  final String key;
}

/// Where the fingerprint log-in key is kept: the phone's secure storage,
/// like the sign-in token. Kept after logging out, which is the point.
abstract class FingerprintStore {
  Future<SavedFingerprint?> read();
  Future<void> write(SavedFingerprint saved);
  Future<void> clear();
}

/// Keychain / Keystore-backed storage.
class SecureFingerprintStore implements FingerprintStore {
  static const _emailKey = 'nurtura_fingerprint_email';
  static const _keyKey = 'nurtura_fingerprint_key';
  final _storage = const FlutterSecureStorage();

  @override
  Future<SavedFingerprint?> read() async {
    final email = await _storage.read(key: _emailKey);
    final key = await _storage.read(key: _keyKey);
    if (email == null || key == null) return null;
    return SavedFingerprint(email: email, key: key);
  }

  @override
  Future<void> write(SavedFingerprint saved) async {
    await _storage.write(key: _emailKey, value: saved.email);
    await _storage.write(key: _keyKey, value: saved.key);
  }

  @override
  Future<void> clear() async {
    await _storage.delete(key: _emailKey);
    await _storage.delete(key: _keyKey);
  }
}

/// In-memory storage for tests.
class MemoryFingerprintStore implements FingerprintStore {
  MemoryFingerprintStore([this.saved]);

  SavedFingerprint? saved;

  @override
  Future<SavedFingerprint?> read() async => saved;

  @override
  Future<void> write(SavedFingerprint saved) async => this.saved = saved;

  @override
  Future<void> clear() async => saved = null;
}
