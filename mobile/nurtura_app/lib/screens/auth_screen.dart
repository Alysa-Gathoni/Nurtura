import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../services/api_client.dart';
import '../state/auth_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../theme/domain_style.dart';
import '../widgets/app_card.dart';
import '../widgets/app_text_field.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';
import '../widgets/password_strength_meter.dart';
import '../widgets/segmented_toggle.dart';
import '../widgets/village.dart';
import '../widgets/google_button.dart';
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

  Future<void> _google() async {
    if (_submitting) return;
    setState(() {
      _error = null;
      _submitting = true;
    });
    try {
      await context.read<AuthState>().continueWithGoogle();
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
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
                                  _Greeting(registering: _registering),
                                  const SizedBox(height: 16),
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
                                        ? "A phrase you'll remember"
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
                                    PasswordStrengthMeter(
                                      password: _password,
                                      email: _email,
                                    ),
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
                                  if (context
                                      .watch<AuthState>()
                                      .googleAvailable) ...[
                                    const SizedBox(height: 10),
                                    const _OrDivider(),
                                    const SizedBox(height: 14),
                                    GoogleButton(
                                      key: const Key('googleButton'),
                                      onPressed: _submitting ? null : _google,
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 18),
                        const _Promises(),
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

/// "or", between the email form and Continue with Google.
class _OrDivider extends StatelessWidget {
  const _OrDivider();

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return Row(
      children: [
        Expanded(child: Divider(color: p.border)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Text(
            'or',
            style: AppText.nunito(
              size: 13.5,
              weight: FontWeight.w700,
              color: p.mutedText,
            ),
          ),
        ),
        Expanded(child: Divider(color: p.border)),
      ],
    );
  }
}

/// "Welcome back" or "Join the village", with a line about the app.
class _Greeting extends StatelessWidget {
  const _Greeting({required this.registering});

  final bool registering;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final (title, line) = registering
        ? (
            'Join the village',
            'Simple, evidence-based play ideas from pregnancy to age 3.',
          )
        : ('Welcome back', 'Pick up where you left off with your little one.');
    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 220),
      child: Column(
        key: ValueKey(registering),
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            key: const Key('authGreeting'),
            style: AppText.quicksand(size: 24, color: p.ink),
          ),
          const SizedBox(height: 2),
          Text(
            line,
            style: AppText.nunito(
              size: 14.5,
              weight: FontWeight.w600,
              color: p.mutedText,
            ),
          ),
        ],
      ),
    );
  }
}

/// Three short promises under the form: what a caregiver gets.
class _Promises extends StatelessWidget {
  const _Promises();

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    const items = [
      (Icons.wb_sunny_rounded, 'Ideas for today'),
      (Icons.lightbulb_rounded, 'A reason for each'),
      (Icons.verified_rounded, 'CDC & WHO guidance'),
    ];
    return Row(
      key: const Key('authPromises'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final (icon, label) in items)
          Expanded(
            child: Column(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: p.primarySoft,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(icon, size: 18, color: p.primary),
                ),
                const SizedBox(height: 6),
                Text(
                  label,
                  textAlign: TextAlign.center,
                  style: AppText.nunito(
                    size: 12.5,
                    weight: FontWeight.w700,
                    color: p.mutedText,
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

/// The brand on a watercolour wash: the five developmental areas pop out
/// around the mark (#140), then the proverb Nurtura is built on. A one-off
/// entrance, skipped when the phone asks for fewer animations.
class _Hero extends StatefulWidget {
  const _Hero();

  @override
  State<_Hero> createState() => _HeroState();
}

class _HeroState extends State<_Hero> with SingleTickerProviderStateMixin {
  late final _entrance = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 1300),
  );

  /// Where each area sits, along the top of an ellipse around the mark.
  static const _angles = [170.0, 130.0, 90.0, 50.0, 10.0];

  /// The mark sits a little below the middle, so the areas arch over it.
  static const _markOffset = Offset(0, 20);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (MediaQuery.of(context).disableAnimations) {
      _entrance.value = 1;
    } else if (_entrance.isDismissed) {
      _entrance.forward();
    }
  }

  @override
  void dispose() {
    _entrance.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return VillageWash(
      seed: 7,
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(24, 6, 24, 54),
          child: Column(
            children: [
              SizedBox(
                key: const Key('authVillage'),
                width: 300,
                height: 150,
                child: AnimatedBuilder(
                  animation: _entrance,
                  builder: (context, _) => Stack(
                    alignment: Alignment.center,
                    clipBehavior: Clip.none,
                    children: [
                      for (var i = 0; i < developmentalDomains.length; i++)
                        _area(context, i),
                      Transform.translate(
                        offset: _markOffset,
                        child: Transform.scale(
                          scale: Curves.easeOutBack.transform(
                            const Interval(0, 0.45).transform(_entrance.value),
                          ),
                          child: const VillageMark(size: 84),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 6),
              Text('Nurtura', style: AppText.quicksand(size: 34, color: p.ink)),
              const SizedBox(height: 2),
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

  /// One area's icon, flying out from behind the mark to its place.
  Widget _area(BuildContext context, int i) {
    final p = context.palette;
    final style = DomainStyle.of(developmentalDomains[i], p);
    final start = 0.3 + i * 0.1;
    final t = Curves.easeOutBack.transform(
      Interval(start, math.min(start + 0.4, 1)).transform(_entrance.value),
    );
    final rad = _angles[i] * math.pi / 180;
    final target = Offset(
      110 * math.cos(rad),
      _markOffset.dy - 70 * math.sin(rad),
    );
    return Transform.translate(
      offset: Offset.lerp(_markOffset, target, t)!,
      child: Transform.scale(
        scale: t.clamp(0.0, 1.2),
        child: Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            color: style.background,
            shape: BoxShape.circle,
            border: Border.all(color: p.card, width: 3),
            boxShadow: [
              BoxShadow(
                color: style.color.withValues(alpha: 0.25),
                blurRadius: 10,
                offset: const Offset(0, 3),
              ),
            ],
          ),
          child: Icon(style.icon, size: 20, color: style.color),
        ),
      ),
    );
  }
}
