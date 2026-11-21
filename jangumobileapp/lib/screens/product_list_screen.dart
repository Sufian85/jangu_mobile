import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/theme.dart';
import '../providers/product_list_provider.dart';
import '../services/catalogue_api.dart';
import '../widgets/message_view.dart';
import '../widgets/product_card.dart';

/// Every product, or those in one category or matching a search. More load
/// automatically as the user nears the bottom of the list.
class ProductListScreen extends StatelessWidget {
  const ProductListScreen({
    super.key,
    required this.title,
    this.categorySlug,
    this.search,
  });

  final String title;
  final String? categorySlug;
  final String? search;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (context) => ProductListProvider(
        context.read<CatalogueApi>(),
        categorySlug: categorySlug,
        search: search,
      )..refresh(),
      child: Scaffold(
        appBar: AppBar(title: Text(title, overflow: TextOverflow.ellipsis)),
        body: const _ProductGrid(),
      ),
    );
  }
}

class _ProductGrid extends StatelessWidget {
  const _ProductGrid();

  @override
  Widget build(BuildContext context) {
    final list = context.watch<ProductListProvider>();

    if (list.items.isEmpty) {
      if (list.isLoading) return const Center(child: CircularProgressIndicator());
      if (list.error != null) {
        return MessageView(
          icon: Icons.cloud_off_outlined,
          title: "Couldn't load products",
          message: list.error,
          actionLabel: 'Try again',
          onAction: list.refresh,
        );
      }
      return const MessageView(
        icon: Icons.search_off,
        title: 'No products found',
      );
    }

    return NotificationListener<ScrollNotification>(
      onNotification: (notification) {
        if (notification.metrics.extentAfter < 400) list.loadMore();
        return false;
      },
      child: RefreshIndicator(
        onRefresh: list.refresh,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 10),
              sliver: SliverToBoxAdapter(
                child: Text(
                  list.totalCount == 1 ? '1 product' : '${list.totalCount} products',
                  style: Theme.of(context)
                      .textTheme
                      .bodySmall
                      ?.copyWith(color: AppColors.muted),
                ),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              sliver: SliverGrid.builder(
                gridDelegate: productGridDelegate,
                itemCount: list.items.length,
                itemBuilder: (_, index) => ProductCard(product: list.items[index]),
              ),
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: list.isLoadingMore
                    ? const Center(child: CircularProgressIndicator())
                    : const SizedBox.shrink(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
