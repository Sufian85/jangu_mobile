import 'package:flutter/material.dart';

import '../core/theme.dart';
import 'brand_logo.dart';

/// The card layout shared by the log in and register screens.
class AuthFormCard extends StatelessWidget {
  const AuthFormCard({
    super.key,
    required this.title,
    required this.subtitle,
    required this.form,
    required this.footerText,
    required this.footerAction,
    required this.onFooterAction,
    this.error,
  });

  final String title;
  final String subtitle;
  final Widget form;
  final String footerText;
  final String footerAction;
  final VoidCallback onFooterAction;
  final String? error;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: const BrandLogo()),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(22),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        title,
                        style: text.titleLarge?.copyWith(fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        subtitle,
                        style: text.bodyMedium?.copyWith(color: AppColors.muted),
                      ),
                      const SizedBox(height: 20),
                      if (error != null) ...[
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: const Color(0xFFFBE9E9),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Text(
                            error!,
                            style: text.bodySmall?.copyWith(
                              color: const Color(0xFFA12D2D),
                            ),
                          ),
                        ),
                        const SizedBox(height: 14),
                      ],
                      form,
                      const SizedBox(height: 12),
                      Wrap(
                        alignment: WrapAlignment.center,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Text(
                            footerText,
                            style: text.bodySmall?.copyWith(color: AppColors.muted),
                          ),
                          TextButton(
                            onPressed: onFooterAction,
                            child: Text(footerAction),
                          ),
                        ],
                      ),
                    ],
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
