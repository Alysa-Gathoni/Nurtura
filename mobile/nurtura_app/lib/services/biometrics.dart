import 'package:flutter/foundation.dart';
import 'package:local_auth/local_auth.dart';

/// The phone's fingerprint (or other biometric) check, for "Unlock with
/// fingerprint" (#150). Behind an interface so tests can stand in for it.
/// The fingerprint never reaches Nurtura: the phone only answers yes or no.
abstract class Biometrics {
  /// Whether the phone can check a fingerprint (or face) right now.
  Future<bool> available();

  /// Shows the phone's prompt with [reason]. True if the person passed;
  /// false if they cancelled or failed. The phone's PIN or pattern is
  /// accepted too. Throws [BiometricsError] with a readable message when
  /// the check can't run (for example, too many tries).
  Future<bool> check(String reason);
}

class BiometricsError implements Exception {
  const BiometricsError(this.message);

  final String message;

  @override
  String toString() => message;
}

/// [Biometrics] with the local_auth plugin.
class LocalAuthBiometrics implements Biometrics {
  final _auth = LocalAuthentication();

  @override
  Future<bool> available() async {
    try {
      return await _auth.isDeviceSupported() &&
          await _auth.canCheckBiometrics &&
          (await _auth.getAvailableBiometrics()).isNotEmpty;
    } catch (e) {
      debugPrint('Biometrics unavailable: $e');
      return false;
    }
  }

  @override
  Future<bool> check(String reason) async {
    try {
      return await _auth.authenticate(
        localizedReason: reason,
        persistAcrossBackgrounding: true,
      );
    } on LocalAuthException catch (e) {
      // Closing the prompt isn't an error: the lock screen just stays.
      if (e.code == LocalAuthExceptionCode.userCanceled ||
          e.code == LocalAuthExceptionCode.systemCanceled ||
          e.code == LocalAuthExceptionCode.timeout) {
        return false;
      }
      throw BiometricsError(switch (e.code) {
        LocalAuthExceptionCode.temporaryLockout ||
        LocalAuthExceptionCode.biometricLockout =>
          'Too many tries. Wait a moment, or log in with your password.',
        _ => "Your phone couldn't check your fingerprint just now.",
      });
    }
  }
}

/// No biometrics: the switch is hidden and the app never locks.
class NoBiometrics implements Biometrics {
  const NoBiometrics();

  @override
  Future<bool> available() async => false;

  @override
  Future<bool> check(String reason) async => false;
}
