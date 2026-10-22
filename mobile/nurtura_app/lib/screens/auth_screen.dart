import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../services/api_client.dart';
import '../state/auth_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../widgets/app_card.dart';
import '../widgets/app_text_field.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';
import '../widgets/segmented_toggle.dart';
import '../widgets/village.dart';
import 'forgot_password_screen.dart';

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
      // Accepted: let the password manager offer to save it.
      TextInput.finishAutofillContext();
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
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const _Hero(),
            Transform.translate(
              // The form card overlaps the bottom of the hero.
              offset: const Offset(0, -34),
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 440),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        AppCard(
                          padding: const EdgeInsets.all(18),
                          child: Form(
                            key: _formKey,
                            child: AutofillGroup(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.stretch,
                                children: [
                                  SegmentedToggle(
                                    options: const ['Log in', 'Register'],
                                    selected: _registering ? 1 : 0,
                                    onChanged: (i) => _switchMode(i == 1),
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
                                    autofillHints: const [
                                      AutofillHints.username,
                                      AutofillHints.email,
                                    ],
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
                                    onSubmitted: _registering
                                        ? null
                                        : (_) => _submit(),
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
                                        color: context.palette.mutedText,
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
                                      // Lets a suggested strong password
                                      // fill both fields.
                                      autofillHints: const [
                                        AutofillHints.newPassword,
                                      ],
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
                                    label: _registering
                                        ? 'Create account'
                                        : 'Log in',
                                    loading: _submitting,
                                    onPressed: _submit,
                                  ),
                                  if (!_registering) ...[
                                    const SizedBox(height: 4),
                                    Center(
                                      child: TextButton(
                                        key: const Key('forgotPasswordButton'),
                                        onPressed: _submitting
                                            ? null
                                            : () => Navigator.of(context).push(
                                                MaterialPageRoute<void>(
                                                  builder: (_) =>
                                                      ForgotPasswordScreen(
                                                        email: _email.text,
                                                      ),
                                                ),
                                              ),
                                        child: const Text('Forgot password?'),
                                      ),
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
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

/// The brand on a watercolour wash, with the proverb Nurtura is built on.
class _Hero extends StatelessWidget {
  const _Hero();

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return VillageWash(
      seed: 7,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 36, 24, 64),
          child: Column(
            children: [
              const VillageMark(size: 92),
              const SizedBox(height: 14),
              Text('Nurtura', style: AppText.quicksand(size: 38, color: p.ink)),
              const SizedBox(height: 4),
              Text(
                'It takes a village to raise a child.',
                textAlign: TextAlign.center,
                style: AppText.nunito(
                  size: 16,
                  weight: FontWeight.w600,
                  color: p.mutedText,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
