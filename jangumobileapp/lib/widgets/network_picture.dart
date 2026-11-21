import 'package:flutter/material.dart';

import '../core/theme.dart';

/// A product photo with a placeholder for missing or broken images.
class NetworkPicture extends StatelessWidget {
  const NetworkPicture({super.key, required this.url, this.fit = BoxFit.contain});

  final String? url;
  final BoxFit fit;

  @override
  Widget build(BuildContext context) {
    final imageUrl = url;
    if (imageUrl == null) return const _Placeholder();
    return Image.network(
      imageUrl,
      fit: fit,
      // Lets images load in a web build even though /media/ sends no CORS headers.
      webHtmlElementStrategy: WebHtmlElementStrategy.fallback,
      errorBuilder: (_, _, _) => const _Placeholder(),
      loadingBuilder: (_, child, progress) {
        if (progress == null) return child;
        return const Center(
          child: SizedBox.square(
            dimension: 20,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        );
      },
    );
  }
}

class _Placeholder extends StatelessWidget {
  const _Placeholder();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Icon(Icons.image_outlined, color: AppColors.inputBorder, size: 40),
    );
  }
}
