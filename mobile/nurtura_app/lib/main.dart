import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'config.dart';
import 'screens/admin/admin_shell.dart';
import 'screens/auth_screen.dart';
import 'screens/home_shell.dart';
import 'screens/lock_screen.dart';
import 'screens/privacy_notice_screen.dart';
import 'screens/verify_code_screen.dart';
import 'services/api_client.dart';
import 'services/biometrics.dart';
import 'services/google_auth.dart';
import 'state/app_lock.dart';
import 'state/auth_state.dart';
import 'state/children_state.dart';
import 'state/device_id_store.dart';
import 'state/engagement.dart';
import 'state/fingerprint_store.dart';
import 'state/preferences.dart';
import 'state/recommendation_cache.dart';
import 'state/theme_state.dart';
import 'state/token_store.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(
    NurturaApp(
      api: ApiClient(baseUrl: apiBaseUrl),
      tokenStore: SecureTokenStore(),
      recommendationCache: SharedPrefsRecommendationCache(),
      preferences: SharedPrefsPreferences(),
      deviceIds: SecureDeviceIdStore(),
      google: googleSignInConfigured
          ? GooglePlayIdTokens(googleServerClientId)
          : null,
      biometrics: LocalAuthBiometrics(),
      fingerprints: SecureFingerprintStore(),
    ),
  );
}

class NurturaApp extends StatelessWidget {
  const NurturaApp({
    super.key,
    required this.api,
    required this.tokenStore,
    required this.recommendationCache,
    required this.preferences,
    required this.deviceIds,
    this.google,
    this.biometrics = const NoBiometrics(),
    this.fingerprints,
  });

  final ApiClient api;
  final TokenStore tokenStore;
  final RecommendationCache recommendationCache;
  final Preferences preferences;
  final DeviceIdStore deviceIds;

  /// Null hides "Continue with Google".
  final GoogleIdTokens? google;

  /// The phone's fingerprint check for "Unlock with fingerprint" (#150).
  final Biometrics biometrics;

  /// Where this phone's fingerprint log-in key is kept (#150).
  final FingerprintStore? fingerprints;

  @override
  Widget build(BuildContext context) {
    final engagement = EngagementState(preferences)..load();
    final children = ChildrenState(api, preferences);
    late final AppLock appLock;
    final auth = AuthState(
      api: api,
      store: tokenStore,
      deviceIds: deviceIds,
      preferences: preferences,
      google: google,
      // Forget this account's data on the phone when it signs out.
      onSessionCleared: () async {
        await recommendationCache.clear();
        await engagement.clear();
        await children.clearSaved();
        appLock.sessionEnded();
      },
      onAccountDeleted: () => appLock.accountDeleted(),
    )..restore();
    appLock = AppLock(
      biometrics,
      fingerprints ?? MemoryFingerprintStore(),
      auth,
    )..load();
    return MultiProvider(
      providers: [
        Provider.value(value: api),
        Provider.value(value: recommendationCache),
        ChangeNotifierProvider(create: (_) => ThemeState(preferences)..load()),
        ChangeNotifierProvider.value(value: engagement),
        ChangeNotifierProvider.value(value: auth),
        ChangeNotifierProvider.value(value: children),
        ChangeNotifierProvider.value(value: appLock),
      ],
      child: Consumer<ThemeState>(
        builder: (context, theme, _) => MaterialApp(
          title: 'Nurtura',
          debugShowCheckedModeBanner: false,
          theme: AppTheme.light(),
          darkTheme: AppTheme.dark(),
          themeMode: theme.mode,
          home: const AuthGate(),
        ),
      ),
    );
  }
}

/// Shows the screen for the current sign-in state, or the lock screen
/// while "Unlock with fingerprint" is on and the app is locked (#150).
class AuthGate extends StatefulWidget {
  const AuthGate({super.key});

  @override
  State<AuthGate> createState() => _AuthGateState();
}

class _AuthGateState extends State<AuthGate> with WidgetsBindingObserver {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final lock = context.read<AppLock>();
    if (state == AppLifecycleState.paused) lock.appLeft();
    if (state == AppLifecycleState.resumed) lock.appReturned();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthState>();
    final lock = context.watch<AppLock>();
    if (auth.status == AuthStatus.signedIn) {
      if (!lock.loaded) {
        return const Scaffold(body: Center(child: CircularProgressIndicator()));
      }
      if (lock.locked) return const LockScreen();
    }
    return switch (auth.status) {
      AuthStatus.unknown => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
      AuthStatus.signedOut => const AuthScreen(),
      AuthStatus.codeRequired => const VerifyCodeScreen(),
      // Administrators get the admin screens (#123); caregivers the app,
      // once they've agreed to the privacy notice (#136).
      AuthStatus.signedIn =>
        auth.isAdministrator
            ? const AdminShell()
            : auth.needsPrivacyConsent
            ? const PrivacyNoticeScreen(consent: true)
            : const HomeShell(),
    };
  }
}
