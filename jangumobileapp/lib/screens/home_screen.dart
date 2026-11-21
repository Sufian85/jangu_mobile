import 'dart:math';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/theme.dart';
import '../models/product.dart';
import '../providers/catalogue_provider.dart';
import '../providers/recent_provider.dart';
import '../widgets/brand_logo.dart';
import '../widgets/category_card.dart';
import '../widgets/message_view.dart';
import '../widgets/product_card.dart';
import '../widgets/section_header.dart';

/// How many products the home page previews before "View more" opens them all.
const int _previewCount = 6;

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  void _viewAll(BuildContext context) => context.push('/products');

  @override
  Widget build(BuildContext context) {
    final catalogue = context.watch<CatalogueProvider>();
    final recent = context.watch<RecentProvider>().items;
    final products = catalogue.latestProducts;

    return Scaffold(
      appBar: AppBar(title: const BrandLogo(), centerTitle: false),
      body: RefreshIndicator(
        onRefresh: catalogue.load,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            const SliverToBoxAdapter(child: _SearchBox()),
            const SliverToBoxAdapter(child: _Banner()),
            if (!catalogue.hasData && catalogue.isLoading)
              const SliverFillRemaining(
                hasScrollBody: false,
                child: Center(child: CircularProgressIndicator()),
              )
            else if (!catalogue.hasData)
              SliverFillRemaining(
                hasScrollBody: false,
                child: MessageView(
                  icon: Icons.cloud_off_outlined,
                  title: "Couldn't load the shop",
                  message: catalogue.error,
                  actionLabel: 'Try again',
                  onAction: catalogue.load,
                ),
              )
            else ...[
              if (catalogue.categories.isNotEmpty) ...[
                const SliverToBoxAdapter(
                  child: SectionHeader(title: 'Shop by category'),
                ),
                SliverPadding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  sliver: SliverGrid.builder(
                    gridDelegate: categoryGridDelegate,
                    itemCount: catalogue.categories.length,
                    itemBuilder: (_, index) {
                      return CategoryCard(category: catalogue.categories[index]);
                    },
                  ),
                ),
              ],
              // New visitors have no history yet, so show the newest products instead.
              SliverToBoxAdapter(
                child: SectionHeader(
                  title: recent.isNotEmpty ? 'Recently viewed' : 'New arrivals',
                ),
              ),
              SliverToBoxAdapter(
                child: _HorizontalProducts(
                  products: recent.isNotEmpty ? recent : products,
                ),
              ),
              SliverToBoxAdapter(
                child: SectionHeader(
                  title: 'Featured products',
                  actionLabel: 'View more',
                  onAction: () => _viewAll(context),
                ),
              ),
              SliverPadding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                sliver: SliverGrid.builder(
                  gridDelegate: productGridDelegate,
                  itemCount: min(_previewCount, products.length),
                  itemBuilder: (_, index) => ProductCard(product: products[index]),
                ),
              ),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
                sliver: SliverToBoxAdapter(
                  child: OutlinedButton(
                    onPressed: () => _viewAll(context),
                    child: const Text('View more products'),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _SearchBox extends StatefulWidget {
  const _SearchBox();

  @override
  State<_SearchBox> createState() => _SearchBoxState();
}

class _SearchBoxState extends State<_SearchBox> {
  final TextEditingController _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _submit(String value) {
    final query = value.trim();
    if (query.isEmpty) return;
    context.push(Uri(path: '/products', queryParameters: {'q': query}).toString());
    _controller.clear();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: TextField(
        controller: _controller,
        textInputAction: TextInputAction.search,
        onSubmitted: _submit,
        decoration: InputDecoration(
          hintText: 'Search for products…',
          prefixIcon: const Icon(Icons.search),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(999),
            borderSide: const BorderSide(color: AppColors.inputBorder),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(999),
            borderSide: const BorderSide(color: AppColors.inputBorder),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(999),
            borderSide: const BorderSide(color: AppColors.navy, width: 1.5),
          ),
        ),
      ),
    );
  }
}

class _Banner extends StatelessWidget {
  const _Banner();

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        gradient: const LinearGradient(
          colors: [AppColors.navy, Color(0xFF1F4E9E)],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Shop Smart · Live Better',
            style: text.labelMedium?.copyWith(color: const Color(0xFFFFD7B3)),
          ),
          const SizedBox(height: 6),
          Text(
            'Your Gadget. Our Priority.',
            style: text.titleLarge?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _HorizontalProducts extends StatelessWidget {
  const _HorizontalProducts({required this.products});

  final List<ProductSummary> products;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 272,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: products.length,
        separatorBuilder: (_, _) => const SizedBox(width: 12),
        itemBuilder: (_, index) {
          return SizedBox(width: 170, child: ProductCard(product: products[index]));
        },
      ),
    );
  }
}
