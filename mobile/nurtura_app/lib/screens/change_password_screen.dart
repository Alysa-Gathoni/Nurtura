import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../services/api_client.dart';
import '../state/auth_state.dart';
import '../theme/app_colors.dart';
import '../widgets/app_card.dart';
import '../widgets/app_text_field.dart';
import '../widgets/buttons.dart';
import '../widgets/message_banner.dart';
import '../widgets/nurtura_app_bar.dart';
import 'forgot_password_screen.dart';

/// Opens the right screen for the signed-in account (#142): Change password,
/// or, for an account made with Google, Set a password with an emailed code.
Future<void> openPasswordSettings(BuildContext context) {
  final user = context.read<AuthState>().user;
  return Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => user == null || user.hasPassword
          ? const ChangePasswordScreen()
          : ForgotPasswordScreen(email: user.email, settingPassword: true),
    ),
  );
}

/// The label for [openPasswordSettings].
String passwordSettingsLabel(BuildContext context) =>
    context.watch<AuthState>().user?.hasPassword == false
    ? 'Set a password'
    : 'Change password';

/// Change the password while signed in (#142): the current one, then a new
/// one. Other phones are signed out.
class ChangePasswordScreen extends StatefulWidget {
  const ChangePasswordScreen({super.key});

  @override
  State<ChangePasswordScreen> createState() => _ChangePasswordScreenState();
}

class _ChangePasswordScreenState extends State<ChangePasswordScreen> {
  final _form = GlobalKey<FormState>();
  final _current = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();

  bool _show = false;
  bool _saving = false;
  ApiException? _error;

  @override
  void dispose() {
    _current.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_saving) return;
    setState(() => _error = null);
    if (!_form.currentState!.validate()) return;
    setState(() => _saving = true);
    final auth = context.read<AuthState>();
    final navigator = Navigator.of(context);
    final messenger = ScaffoldMessenger.of(context);
    try {
      await auth.changePassword(_current.text, _password.text);
      TextInput.finishAutofillContext();
      navigator.pop();
      messenger.showSnackBar(
        const SnackBar(
          content: Text(
            'Password changed. Other phones will need to log in again.',
          ),
        ),
      );
    } on ApiException catch (e) {
      if (!mounted) return;
      if (e.statusCode == 401) {
        navigator.popUntil((route) => route.isFirst);
        await auth.sessionExpired();
        return;
      }
      setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = context.palette;
    final email = context.watch<AuthState>().user?.email ?? '';
    final shown = {'current_password', 'new_password'};
    final banner = _error == null
        ? null
        : _error!.fieldErrors.keys.any(shown.contains)
        ? null
        : _error!.message;
    final toggle = IconButton(
      tooltip: _show ? 'Hide passwords' : 'Show passwords',
      icon: Icon(
        _show ? Icons.visibility_off_rounded : Icons.visibility_rounded,
        color: p.mutedText,
      ),
      onPressed: () => setState(() => _show = !_show),
    );
    return Scaffold(
      appBar: const NurturaAppBar(title: 'Change password'),
      body: SafeArea(
        child: Align(
          alignment: Alignment.topCenter,
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 440),
              child: AppCard(
                padding: const EdgeInsets.all(18),
                child: Form(
                  key: _form,
                  child: AutofillGroup(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          'For $email',
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(height: 14),
                        AppTextField(
                          key: const Key('currentPasswordField'),
                          label: 'Current password',
                          hint: 'The one you use now',
                          controller: _current,
                          prefixIcon: Icons.lock_outline_rounded,
                          obscureText: !_show,
                          textInputAction: TextInputAction.next,
                          autofillHints: const [AutofillHints.password],
                          errorText: _error?.field('current_password'),
                          suffix: toggle,
                          validator: (v) => (v == null || v.isEmpty)
                              ? 'Enter your current password.'
                              : null,
                        ),
                        const SizedBox(height: 14),
                        AppTextField(
                          key: const Key('newPasswordField'),
                          label: 'New password',
                          hint: "A phrase you'll remember",
                          controller: _password,
                          prefixIcon: Icons.lock_reset_rounded,
                          obscureText: !_show,
                          textInputAction: TextInputAction.next,
                          autofillHints: const [AutofillHints.newPassword],
                          errorText: _error?.field('new_password'),
                          validator: (v) => (v == null || v.isEmpty)
                              ? 'Enter a new password.'
                              : null,
                        ),
                        // The strength meter (#140) goes here once
                        // that PR is merged.
                        const SizedBox(height: 14),
                        AppTextField(
                          key: const Key('confirmNewPasswordField'),
                          label: 'Confirm new password',
                          hint: 'Type it again',
                          controller: _confirm,
                          prefixIcon: Icons.lock_reset_rounded,
                          obscureText: !_show,
                          textInputAction: TextInputAction.done,
                          autofillHints: const [AutofillHints.newPassword],
                          onSubmitted: (_) => _save(),
                          validator: (v) => v != _password.text
                              ? "Passwords don't match."
                              : null,
                        ),
                        if (banner != null) ...[
                          const SizedBox(height: 14),
                          MessageBanner.error(
                            banner,
                            key: const Key('changePasswordError'),
                          ),
                        ],
                        const SizedBox(height: 18),
                        PrimaryButton(
                          key: const Key('savePasswordButton'),
                          label: 'Save new password',
                          icon: Icons.check_rounded,
                          loading: _saving,
                          onPressed: _save,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          "You'll stay logged in here; other phones will "
                          'need to log in again.',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
