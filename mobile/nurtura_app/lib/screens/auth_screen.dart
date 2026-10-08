import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_client.dart';
import '../state/auth_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../widgets/app_card.dart';
import '../widgets/app_text_field.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';

/// Register or log in as a caregiver.
class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();

  bool _registering = false;
  bool _submitting = false;
  bool _showPassword = false;
  ApiException? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  void _switchMode(bool registering) {
    if (_submitting || registering == _registering) return;
    setState(() {
      _registering = registering;
      _error = null;
    });
  }

  Future<void> _submit() async {
    if (_submitting) return;
    setState(() => _error = null);
    if (!_formKey.currentState!.validate()) return;

    setState(() => _submitting = true);
    final auth = context.read<AuthState>();
    try {
      if (_registering) {
        await auth.register(_email.text, _password.text);
      } else {
        await auth.login(_email.text, _password.text);
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Errors for the email/password fields appear under them; the banner
    // shows everything else, so no backend message is ever dropped.
    String? bannerMessage;
    if (_error != null) {
      const shown = {'email', 'password'};
      final fields = _error!.fieldErrors;
      final other = [
        for (final entry in fields.entries)
          if (!shown.contains(entry.key)) ...entry.value,
      ];
      final anyShown = fields.keys.any(shown.contains);
      final parts = [if (!anyShown) _error!.message, ...other];
      bannerMessage = parts.isEmpty ? null : parts.join(' ');
    }

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const _Brand(),
                  const SizedBox(height: 24),
                  AppCard(
                    padding: const EdgeInsets.all(18),
                    child: Form(
                      key: _formKey,
                      child: AutofillGroup(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            _ModeToggle(
                              registering: _registering,
                              onChanged: _switchMode,
                            ),
                            const SizedBox(height: 20),
                            AppTextField(
                              key: const Key('emailField'),
                              label: 'Email',
                              hint: 'you@example.com',
                              controller: _email,
                              prefixIcon: Icons.mail_outline_rounded,
                              keyboardType: TextInputType.emailAddress,
                              textInputAction: TextInputAction.next,
                              autofillHints: const [AutofillHints.email],
                              errorText: _error?.field('email'),
                              validator: _validateEmail,
                            ),
                            const SizedBox(height: 14),
                            AppTextField(
                              key: const Key('passwordField'),
                              label: 'Password',
                              hint: _registering
                                  ? 'At least 8 characters'
                                  : 'Your password',
                              controller: _password,
                              prefixIcon: Icons.lock_outline_rounded,
                              obscureText: !_showPassword,
                              textInputAction: _registering
                                  ? TextInputAction.next
                                  : TextInputAction.done,
                              autofillHints: [
                                _registering
                                    ? AutofillHints.newPassword
                                    : AutofillHints.password,
                              ],
                              errorText: _error?.field('password'),
                              onSubmitted: _registering ? null : (_) => _submit(),
                              validator: (v) => (v == null || v.isEmpty)
                                  ? 'Enter your password.'
                                  : null,
                              suffix: IconButton(
                                tooltip: _showPassword
                                    ? 'Hide password'
                                    : 'Show password',
                                icon: Icon(
                                  _showPassword
                                      ? Icons.visibility_off_rounded
                                      : Icons.visibility_rounded,
                                  color: AppColors.mutedText,
                                ),
                                onPressed: () => setState(
                                  () => _showPassword = !_showPassword,
                                ),
                              ),
                            ),
                            if (_registering) ...[
                              const SizedBox(height: 14),
                              AppTextField(
                                key: const Key('confirmField'),
                                label: 'Confirm password',
                                hint: 'Type it again',
                                controller: _confirm,
                                prefixIcon: Icons.lock_outline_rounded,
                                obscureText: !_showPassword,
                                textInputAction: TextInputAction.done,
                                onSubmitted: (_) => _submit(),
                                validator: (v) => v != _password.text
                                    ? "Passwords don't match."
                                    : null,
                              ),
                            ],
                            if (bannerMessage != null) ...[
                              const SizedBox(height: 16),
                              MessageBanner.error(
                                bannerMessage,
                                key: const Key('authError'),
                              ),
                            ],
                            const SizedBox(height: 20),
                            PrimaryButton(
                              key: const Key('submitButton'),
                              label: _registering ? 'Create account' : 'Log in',
                              loading: _submitting,
                              onPressed: _submit,
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    _registering
                        ? 'You are creating a caregiver account.'
                        : 'New to Nurtura? Choose Register above.',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  static String? _validateEmail(String? value) {
    final email = value?.trim() ?? '';
    if (email.isEmpty) return 'Enter your email address.';
    if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email)) {
      return "That doesn't look like an email address.";
    }
    return null;
  }
}

class _Brand extends StatelessWidget {
  const _Brand();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: const LinearGradient(
              colors: [AppColors.teal, AppColors.tealLight],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            boxShadow: AppShadows.primaryButton,
          ),
          child: const Icon(Icons.spa_rounded, color: Colors.white, size: 36),
        ),
        const SizedBox(height: 14),
        Text(
          'Nurtura',
          style: AppText.quicksand(size: 34, color: AppColors.tealDeep),
        ),
        const SizedBox(height: 4),
        Text(
          "Everyday activities for your child's growth",
          textAlign: TextAlign.center,
          style: AppText.nunito(
            size: 15,
            weight: FontWeight.w600,
            color: AppColors.mutedText,
          ),
        ),
      ],
    );
  }
}

/// Pill-shaped Log in / Register switch.
class _ModeToggle extends StatelessWidget {
  const _ModeToggle({required this.registering, required this.onChanged});

  final bool registering;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: const ShapeDecoration(
        color: AppColors.mint,
        shape: StadiumBorder(),
      ),
      child: Row(
        children: [
          _segment('Log in', !registering, () => onChanged(false)),
          _segment('Register', registering, () => onChanged(true)),
        ],
      ),
    );
  }

  Widget _segment(String label, bool active, VoidCallback onTap) {
    return Expanded(
      child: Material(
        key: Key('mode_$label'),
        color: active ? AppColors.tealDeep : Colors.transparent,
        shape: const StadiumBorder(),
        child: InkWell(
          customBorder: const StadiumBorder(),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 10),
            child: Text(
              label,
              textAlign: TextAlign.center,
              style: AppText.nunito(
                size: 15,
                weight: FontWeight.w800,
                color: active ? Colors.white : AppColors.tealDeep,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
