import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/theme.dart';
import '../models/category.dart';

/// Layout shared by every category grid.
const SliverGridDelegate categoryGridDelegate =
    SliverGridDelegateWithMaxCrossAxisExtent(
  maxCrossAxisExtent: 200,
  mainAxisExtent: 112,
  crossAxisSpacing: 12,
  mainAxisSpacing: 12,
);

class CategoryCard extends StatelessWidget {
  const CategoryCard({super.key, required this.category});

  final Category category;

  IconData get _icon {
    final name = category.name.toLowerCase();
    if (name.contains('phone')) return Icons.smartphone;
    if (name.contains('laptop') || name.contains('computer')) return Icons.laptop_mac;
    if (name.contains('audio') || name.contains('wearable')) return Icons.headphones;
    if (name.contains('gaming') || name.contains('game')) return Icons.sports_esports;
    return Icons.category_outlined;
  }

  @override
  Widget build(BuildContext context) {
    final location = Uri(
      path: '/categories/${category.slug}',
      queryParameters: {'name': category.name},
    );
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => context.push(location.toString()),
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(_icon, color: AppColors.navy, size: 30),
              const SizedBox(height: 8),
              Text(
                category.name,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
