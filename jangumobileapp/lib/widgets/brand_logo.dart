import 'package:flutter/material.dart';

import '../core/theme.dart';

class BrandLogo extends StatelessWidget {
  const BrandLogo({super.key, this.size = 22});

  final double size;

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(context).textTheme.titleLarge?.copyWith(
          fontSize: size,
          fontWeight: FontWeight.w700,
          color: AppColors.navy,
        );
    return Text.rich(
      TextSpan(
        text: 'Jan',
        style: style,
        children: [
          TextSpan(text: 'gu', style: style?.copyWith(color: AppColors.orange)),
        ],
      ),
    );
  }
}
