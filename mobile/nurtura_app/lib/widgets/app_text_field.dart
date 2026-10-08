import 'package:flutter/material.dart';

import '../theme/app_colors.dart';
import '../theme/app_theme.dart';

/// Labelled text field: white fill, 12px radius, 2px mint border.
class AppTextField extends StatelessWidget {
  const AppTextField({
    super.key,
    required this.label,
    this.controller,
    this.hint,
    this.errorText,
    this.obscureText = false,
    this.keyboardType,
    this.textInputAction,
    this.autofillHints,
    this.validator,
    this.onSubmitted,
    this.onChanged,
    this.prefixIcon,
    this.suffix,
    this.enabled = true,
  });

  final String label;
  final TextEditingController? controller;
  final String? hint;
  final String? errorText;
  final bool obscureText;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final Iterable<String>? autofillHints;
  final FormFieldValidator<String>? validator;
  final ValueChanged<String>? onSubmitted;
  final ValueChanged<String>? onChanged;
  final IconData? prefixIcon;
  final Widget? suffix;
  final bool enabled;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 4, bottom: 6),
          child: Text(
            label,
            style: AppText.nunito(size: 13.5, weight: FontWeight.w800),
          ),
        ),
        TextFormField(
          controller: controller,
          obscureText: obscureText,
          keyboardType: keyboardType,
          textInputAction: textInputAction,
          autofillHints: autofillHints,
          validator: validator,
          onFieldSubmitted: onSubmitted,
          onChanged: onChanged,
          enabled: enabled,
          style: AppText.nunito(size: 15.5, weight: FontWeight.w600),
          decoration: InputDecoration(
            hintText: hint,
            errorText: errorText,
            errorMaxLines: 3,
            prefixIcon: prefixIcon == null
                ? null
                : Icon(prefixIcon, color: AppColors.mutedText),
            suffixIcon: suffix,
          ),
        ),
      ],
    );
  }
}
