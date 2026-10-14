import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'config.dart';
import 'screens/auth_screen.dart';
import 'screens/children_screen.dart';
import 'services/api_client.dart';
import 'state/auth_state.dart';
import 'state/children_state.dart';
import 'state/recommendation_cache.dart';
import 'state/token_store.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(
    NurturaApp(
      api: ApiClient(baseUrl: apiBaseUrl),
      tokenStore: SecureTokenStore(),
      recommendationCache: SharedPrefsRecommendationCache(),
    ),
  );
}

class NurturaApp extends StatelessWidget {
  const NurturaApp({
    super.key,
    required this.api,
    required this.tokenStore,
    required this.recommendationCache,
  });

  final ApiClient api;
  final TokenStore tokenStore;
  final RecommendationCache recommendationCache;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider.value(value: api),
        Provider.value(value: recommendationCache),
        ChangeNotifierProvider(
          create: (_) => AuthState(
            api: api,
            store: tokenStore,
            onSessionCleared: recommendationCache.clear,
          )..restore(),
        ),
        ChangeNotifierProvider(create: (_) => ChildrenState(api)),
      ],
      child: MaterialApp(
        title: 'Nurtura',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        home: const AuthGate(),
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
      AuthStatus.signedIn => const ChildrenScreen(),
    };
  }
}
