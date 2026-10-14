import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'config.dart';
import 'screens/auth_screen.dart';
import 'screens/home_shell.dart';
import 'screens/verify_code_screen.dart';
import 'services/api_client.dart';
import 'state/auth_state.dart';
import 'state/children_state.dart';
import 'state/device_id_store.dart';
import 'state/engagement.dart';
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
  });

  final ApiClient api;
  final TokenStore tokenStore;
  final RecommendationCache recommendationCache;
  final Preferences preferences;
  final DeviceIdStore deviceIds;

  @override
  Widget build(BuildContext context) {
    final engagement = EngagementState(preferences)..load();
    final children = ChildrenState(api, preferences);
    return MultiProvider(
      providers: [
        Provider.value(value: api),
        Provider.value(value: recommendationCache),
        ChangeNotifierProvider(create: (_) => ThemeState(preferences)..load()),
        ChangeNotifierProvider.value(value: engagement),
        ChangeNotifierProvider(
          create: (_) => AuthState(
            api: api,
            store: tokenStore,
            deviceIds: deviceIds,
            // Forget this account's data on the phone when it signs out.
            onSessionCleared: () async {
              await recommendationCache.clear();
              await engagement.clear();
              await children.clearSaved();
            },
          )..restore(),
        ),
        ChangeNotifierProvider.value(value: children),
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

/// Shows the screen for the current sign-in state.
class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return switch (context.watch<AuthState>().status) {
      AuthStatus.unknown => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
      AuthStatus.signedOut => const AuthScreen(),
      AuthStatus.codeRequired => const VerifyCodeScreen(),
      AuthStatus.signedIn => const HomeShell(),
    };
  }
}
