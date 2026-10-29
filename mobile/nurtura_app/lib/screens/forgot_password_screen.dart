import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../services/api_client.dart';
import '../services/auth_service.dart';
import '../state/auth_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../widgets/password_strength_meter.dart';
import '../widgets/app_card.dart';
import '../widgets/app_text_field.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';
import 'verify_code_screen.dart';

/// Choosing a new password with an emailed code (#126): the email first,
/// then the code and the new password. Success signs in on this phone.
class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({
    super.key,
    this.email = '',
    this.settingPassword = false,
  });

  /// What was typed on the login form, to start from.
  final String email;

  /// A signed-in account made with Google setting its first password
  /// (#142): the email is its own and can't be changed.
  final bool settingPassword;

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _emailForm = GlobalKey<FormState>();
  final _resetForm = GlobalKey<FormState>();
  late final _email = TextEditingController(text: widget.email.trim());
  final _code = TextEditingController();
  final _codeFocus = FocusNode();
  final _password = TextEditingController();
  final _confirm = TextEditingController();

  CodeChallenge? _challenge;
  bool _busy = false;
  bool _showPassword = false;
  bool _remember = true;
  String? _error;
  String? _passwordError;
  String? _notice;
  int _wait = 0;
  Timer? _timer;

  @override
  void dispose() {
    _timer?.cancel();
    _email.dispose();
    _code.dispose();
    _codeFocus.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  void _startCountdown(int seconds) {
    _timer?.cancel();
    setState(() => _wait = seconds);
    if (seconds <= 0) return;
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) return t.cancel();
      setState(() => _wait--);
      if (_wait <= 0) t.cancel();
    });
  }

  Future<void> _sendCode() async {
    if (_busy || !_emailForm.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final challenge = await context.read<AuthState>().requestPasswordReset(
        _email.text,
      );
      if (!mounted) return;
      setState(() => _challenge = challenge);
      _startCountdown(challenge.resendAfter.inSeconds);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _resend() async {
    final challenge = _challenge;
    if (challenge == null || _busy || _wait > 0) return;
    setState(() {
      _busy = true;
      _error = null;
      _notice = null;
    });
    try {
      final fresh = await context.read<AuthState>().resendPasswordReset(
        challenge,
      );
      if (!mounted) return;
      _code.clear();
      setState(() {
        _challenge = fresh;
        _notice = 'A new code is on its way.';
      });
      _startCountdown(fresh.resendAfter.inSeconds);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _reset() async {
    final challenge = _challenge;
    if (challenge == null || _busy) return;
    setState(() {
      _error = null;
      _passwordError = null;
      _notice = null;
    });
    final codeOk = _code.text.length == VerifyCodeScreen.codeLength;
    final formOk = _resetForm.currentState!.validate();
    if (!codeOk) {
      setState(() => _error = 'Enter all six digits from the email.');
    }
    if (!codeOk || !formOk) return;

    setState(() => _busy = true);
    final navigator = Navigator.of(context);
    try {
      await context.read<AuthState>().resetPassword(
        challenge,
        _code.text,
        _password.text,
        rememberDevice: _remember,
      );
      // Saved: let the password manager offer to store the new password,
      // then the app underneath shows the home screens.
      TextInput.finishAutofillContext();
      navigator.popUntil((route) => route.isFirst);
    } on ApiException catch (e) {
      if (!mounted) return;
      final passwordErrors = e.fieldErrors['new_password'];
      setState(() {
        if (passwordErrors != null) {
          _passwordError = passwordErrors.join(' ');
        } else {
          _error = e.message;
          _code.clear();
        }
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final challenge = _challenge;
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: BackButton(
          key: const Key('resetBack'),
          onPressed: _busy ? null : () => Navigator.of(context).pop(),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Center(
                    child: Container(
                      width: 84,
                      height: 84,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: p.mustardSoft,
                      ),
                      child: Icon(
                        challenge == null
                            ? Icons.key_rounded
                            : Icons.mark_email_read_rounded,
                        color: p.mustard,
                        size: 40,
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  Text(
                    challenge != null
                        ? 'Check your email'
                        : widget.settingPassword
                        ? 'Set a password'
                        : 'Forgot your password?',
                    textAlign: TextAlign.center,
                    style: AppText.quicksand(size: 28, color: p.ink),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    challenge == null
                        ? widget.settingPassword
                              ? "We'll email you a code to check it's you. "
                                    'Then you can also log in with your email.'
                              : "We'll email you a code to choose a new one."
                        : 'If ${challenge.emailHint} has a Nurtura account, '
                              'we sent it a 6-digit code.',
                    key: const Key('resetHint'),
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 22),
                  AppCard(
                    padding: const EdgeInsets.all(18),
                    child: challenge == null ? _emailStep() : _resetStep(),
                  ),
                  if (challenge != null) ...[
                    const SizedBox(height: 16),
                    TextButton(
                      key: const Key('resetResendButton'),
                      onPressed: _wait > 0 || _busy ? null : _resend,
                      child: Text(
                        _wait > 0
                            ? 'Send a new code in ${_wait}s'
                            : 'Send a new code',
                      ),
                    ),
                    if (!widget.settingPassword)
                      TextButton(
                        key: const Key('resetDifferentEmail'),
                        onPressed: _busy
                            ? null
                            : () {
                                _timer?.cancel();
                                _code.clear();
                                setState(() {
                                  _challenge = null;
                                  _error = null;
                                  _notice = null;
                                  _passwordError = null;
                                });
                              },
                        child: const Text('Use a different email'),
                      ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _emailStep() => Form(
    key: _emailForm,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppTextField(
          key: const Key('resetEmailField'),
          readOnly: widget.settingPassword,
          label: 'Email',
          hint: 'you@example.com',
          controller: _email,
          prefixIcon: Icons.mail_outline_rounded,
          keyboardType: TextInputType.emailAddress,
          textInputAction: TextInputAction.done,
          autofillHints: const [AutofillHints.username, AutofillHints.email],
          onSubmitted: (_) => _sendCode(),
          validator: (v) {
            final email = v?.trim() ?? '';
            if (email.isEmpty) return 'Enter your email address.';
            if (!RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(email)) {
              return "That doesn't look like an email address.";
            }
            return null;
          },
        ),
        if (_error != null) ...[
          const SizedBox(height: 14),
          MessageBanner.error(_error!, key: const Key('resetError')),
        ],
        const SizedBox(height: 18),
        PrimaryButton(
          key: const Key('sendResetCodeButton'),
          label: 'Email me a code',
          icon: Icons.send_rounded,
          loading: _busy,
          onPressed: _sendCode,
        ),
      ],
    ),
  );

  Widget _resetStep() {
    final p = context.palette;
    final toggle = IconButton(
      tooltip: _showPassword ? 'Hide password' : 'Show password',
      icon: Icon(
        _showPassword ? Icons.visibility_off_rounded : Icons.visibility_rounded,
        color: p.mutedText,
      ),
      onPressed: () => setState(() => _showPassword = !_showPassword),
    );
    return Form(
      key: _resetForm,
      child: AutofillGroup(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // The account the new password is for, so "Suggest strong
            // password" and saving the password work.
            AppTextField(
              key: const Key('resetAccountField'),
              label: 'Account',
              controller: _email,
              prefixIcon: Icons.mail_outline_rounded,
              readOnly: true,
              autofillHints: const [
                AutofillHints.username,
                AutofillHints.email,
              ],
            ),
            const SizedBox(height: 18),
            CodeBoxes(
              controller: _code,
              focusNode: _codeFocus,
              enabled: !_busy,
              onChanged: (_) => setState(() => _error = null),
            ),
            const SizedBox(height: 18),
            AppTextField(
              key: const Key('newPasswordField'),
              label: 'New password',
              hint: "A phrase you'll remember",
              controller: _password,
              prefixIcon: Icons.lock_outline_rounded,
              obscureText: !_showPassword,
              textInputAction: TextInputAction.next,
              autofillHints: const [AutofillHints.newPassword],
              errorText: _passwordError,
              suffix: toggle,
              validator: (v) =>
                  (v == null || v.isEmpty) ? 'Enter a new password.' : null,
            ),
            PasswordStrengthMeter(password: _password, email: _email),
            const SizedBox(height: 14),
            AppTextField(
              key: const Key('confirmNewPasswordField'),
              label: 'Confirm new password',
              hint: 'Type it again',
              controller: _confirm,
              prefixIcon: Icons.lock_outline_rounded,
              obscureText: !_showPassword,
              textInputAction: TextInputAction.done,
              autofillHints: const [AutofillHints.newPassword],
              onSubmitted: (_) => _reset(),
              validator: (v) =>
                  v != _password.text ? "Passwords don't match." : null,
            ),
            const SizedBox(height: 6),
            SwitchListTile.adaptive(
              key: const Key('resetRememberDevice'),
              contentPadding: EdgeInsets.zero,
              value: _remember,
              onChanged: _busy ? null : (v) => setState(() => _remember = v),
              title: Text(
                'Trust this phone for 30 days',
                style: AppText.nunito(
                  size: 15,
                  weight: FontWeight.w700,
                  color: p.ink,
                ),
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              MessageBanner.error(_error!, key: const Key('resetError')),
            ],
            if (_notice != null && _error == null) ...[
              const SizedBox(height: 8),
              MessageBanner.success(_notice!),
            ],
            const SizedBox(height: 16),
            PrimaryButton(
              key: const Key('resetPasswordButton'),
              label: 'Save and sign in',
              icon: Icons.lock_reset_rounded,
              loading: _busy,
              onPressed: _reset,
            ),
          ],
        ),
      ),
    );
  }
}
