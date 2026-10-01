import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'config.dart';
import 'screens/auth_screen.dart';
import 'screens/home_screen.dart';
import 'services/api_client.dart';
import 'state/auth_state.dart';
import 'state/token_store.dart';
import 'theme/app_theme.dart';

void main() {
  runApp(
    NurturaApp(
      api: ApiClient(baseUrl: apiBaseUrl),
      tokenStore: SecureTokenStore(),
    ),
  );
}

class NurturaApp extends StatelessWidget {
  const NurturaApp({super.key, required this.api, required this.tokenStore});

  final ApiClient api;
  final TokenStore tokenStore;

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider.value(value: api),
        ChangeNotifierProvider(
          create: (_) => AuthState(api: api, store: tokenStore)..restore(),
        ),
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
      AuthStatus.signedIn => const HomeScreen(),
    };
  }
}
