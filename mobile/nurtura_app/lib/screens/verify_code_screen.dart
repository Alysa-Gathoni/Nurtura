import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../services/api_client.dart';
import '../state/auth_state.dart';
import '../theme/app_colors.dart';
import '../theme/app_theme.dart';
import '../widgets/app_card.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';

/// The second sign-in step: the six-digit code emailed to the caregiver
/// (#91). Shown on a phone the account has not trusted yet.
class VerifyCodeScreen extends StatefulWidget {
  const VerifyCodeScreen({super.key});

  static const codeLength = 6;

  @override
  State<VerifyCodeScreen> createState() => _VerifyCodeScreenState();
}

class _VerifyCodeScreenState extends State<VerifyCodeScreen> {
  final _code = TextEditingController();
  final _focus = FocusNode();

  bool _remember = true;
  bool _submitting = false;
  bool _resending = false;
  String? _error;
  String? _notice;
  int _wait = 0;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    final challenge = context.read<AuthState>().challenge;
    _startCountdown(challenge?.resendAfter.inSeconds ?? 30);
  }

  @override
  void dispose() {
    _timer?.cancel();
    _code.dispose();
    _focus.dispose();
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

  void _changed(String value) {
    setState(() => _error = null);
    if (value.length == VerifyCodeScreen.codeLength) _submit();
  }

  Future<void> _submit() async {
    if (_submitting) return;
    if (_code.text.length != VerifyCodeScreen.codeLength) {
      setState(() => _error = 'Enter all six digits from the email.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
      _notice = null;
    });
    try {
      await context.read<AuthState>().verifyCode(
        _code.text,
        rememberDevice: _remember,
      );
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
      _code.clear();
      _focus.requestFocus();
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _resend() async {
    if (_resending || _wait > 0) return;
    setState(() {
      _resending = true;
      _error = null;
      _notice = null;
    });
    try {
      final challenge = await context.read<AuthState>().resendCode();
      if (!mounted) return;
      _code.clear();
      setState(() => _notice = 'A new code is on its way.');
      _startCountdown(challenge?.resendAfter.inSeconds ?? 30);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _resending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final auth = context.watch<AuthState>();
    final hint = auth.challenge?.emailHint ?? 'your email address';

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
                  Center(
                    child: Container(
                      width: 84,
                      height: 84,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: LinearGradient(
                          colors: [p.headerStart, p.headerEnd],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                      ),
                      child: const Icon(
                        Icons.mark_email_read_rounded,
                        color: Colors.white,
                        size: 42,
                      ),
                    ),
                  ),
                  const SizedBox(height: 18),
                  Text(
                    'Check your email',
                    textAlign: TextAlign.center,
                    style: AppText.quicksand(size: 28, color: p.ink),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'We sent a six-digit code to $hint. '
                    'Enter it to finish signing in.',
                    key: const Key('codeHint'),
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 22),
                  AppCard(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        _CodeBoxes(
                          controller: _code,
                          focusNode: _focus,
                          enabled: !_submitting,
                          onChanged: _changed,
                        ),
                        const SizedBox(height: 14),
                        SwitchListTile.adaptive(
                          key: const Key('rememberDevice'),
                          contentPadding: EdgeInsets.zero,
                          value: _remember,
                          onChanged: _submitting
                              ? null
                              : (v) => setState(() => _remember = v),
                          title: Text(
                            'Trust this phone for 30 days',
                            style: AppText.nunito(
                              size: 15,
                              weight: FontWeight.w700,
                              color: p.ink,
                            ),
                          ),
                          subtitle: Text(
                            'Skip the code when you sign in here.',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ),
                        if (_error != null) ...[
                          const SizedBox(height: 8),
                          MessageBanner.error(
                            _error!,
                            key: const Key('codeError'),
                          ),
                        ],
                        if (_notice != null && _error == null) ...[
                          const SizedBox(height: 8),
                          MessageBanner.success(_notice!),
                        ],
                        const SizedBox(height: 16),
                        PrimaryButton(
                          key: const Key('verifyButton'),
                          label: 'Verify and sign in',
                          icon: Icons.verified_user_rounded,
                          loading: _submitting,
                          onPressed: _submit,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextButton(
                    key: const Key('resendButton'),
                    onPressed: _wait > 0 || _resending || _submitting
                        ? null
                        : _resend,
                    child: Text(
                      _wait > 0
                          ? 'Send a new code in ${_wait}s'
                          : 'Send a new code',
                    ),
                  ),
                  TextButton(
                    key: const Key('differentAccountButton'),
                    onPressed: _submitting
                        ? null
                        : context.read<AuthState>().cancelChallenge,
                    child: const Text('Use a different account'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Six boxes over one hidden text field, so paste and the SMS/email
/// autofill suggestion still work.
class _CodeBoxes extends StatelessWidget {
  const _CodeBoxes({
    required this.controller,
    required this.focusNode,
    required this.enabled,
    required this.onChanged,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final bool enabled;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    return GestureDetector(
      onTap: focusNode.requestFocus,
      child: Stack(
        alignment: Alignment.center,
        children: [
          ListenableBuilder(
            listenable: Listenable.merge([controller, focusNode]),
            builder: (context, _) {
              final text = controller.text;
              return Row(
                children: [
                  for (var i = 0; i < VerifyCodeScreen.codeLength; i++) ...[
                    if (i > 0) const SizedBox(width: 8),
                    Expanded(
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 150),
                        height: 56,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: i < text.length ? p.mint : p.cardAlt,
                          borderRadius: BorderRadius.circular(AppRadii.field),
                          border: Border.all(
                            width: 2,
                            color:
                                focusNode.hasFocus &&
                                    i ==
                                        text.length.clamp(
                                          0,
                                          VerifyCodeScreen.codeLength - 1,
                                        )
                                ? p.teal
                                : p.border,
                          ),
                        ),
                        child: Text(
                          i < text.length ? text[i] : '',
                          style: AppText.quicksand(size: 24, color: p.ink),
                        ),
                      ),
                    ),
                  ],
                ],
              );
            },
          ),
          // The real input: invisible, covering the boxes.
          Positioned.fill(
            child: Opacity(
              opacity: 0,
              child: TextField(
                key: const Key('codeField'),
                controller: controller,
                focusNode: focusNode,
                enabled: enabled,
                autofocus: true,
                showCursor: false,
                keyboardType: TextInputType.number,
                autofillHints: const [AutofillHints.oneTimeCode],
                maxLength: VerifyCodeScreen.codeLength,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                decoration: const InputDecoration(
                  counterText: '',
                  border: InputBorder.none,
                ),
                onChanged: onChanged,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
