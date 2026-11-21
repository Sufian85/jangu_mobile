import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/formatters.dart';
import '../core/theme.dart';
import '../models/product.dart';
import '../providers/cart_provider.dart';
import '../providers/recent_provider.dart';
import '../services/catalogue_api.dart';
import '../widgets/message_view.dart';
import '../widgets/network_picture.dart';
import '../widgets/quantity_stepper.dart';

class ProductDetailScreen extends StatefulWidget {
  const ProductDetailScreen({super.key, required this.slug});

  final String slug;

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  ProductDetail? _product;
  ProductVariant? _variant;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (_error != null) setState(() => _error = null);
    try {
      final product = await context.read<CatalogueApi>().fetchProduct(widget.slug);
      if (!mounted) return;
      setState(() {
        _product = product;
        // Start on the first variant that can actually be bought.
        final variants = product.variants;
        _variant = variants.isEmpty
            ? null
            : variants.firstWhere((v) => v.inStock, orElse: () => variants.first);
      });
      context.read<RecentProvider>().add(product.toSummary());
    } on ApiException catch (error) {
      if (mounted) setState(() => _error = error.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final product = _product;
    return Scaffold(
      appBar: AppBar(title: Text(product?.brand ?? '')),
      bottomNavigationBar: product == null
          ? null
          : _BuyBar(product: product, variant: _variant),
      body: product != null
          ? _ProductBody(
              product: product,
              selected: _variant,
              onSelect: (variant) => setState(() => _variant = variant),
            )
          : _error != null
              ? MessageView(
                  icon: Icons.cloud_off_outlined,
                  title: "Couldn't load this product",
                  message: _error,
                  actionLabel: 'Try again',
                  onAction: _load,
                )
              : const Center(child: CircularProgressIndicator()),
    );
  }
}

class _ProductBody extends StatelessWidget {
  const _ProductBody({
    required this.product,
    required this.selected,
    required this.onSelect,
  });

  final ProductDetail product;
  final ProductVariant? selected;
  final ValueChanged<ProductVariant> onSelect;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final variant = selected;
    return ListView(
      children: [
        _Gallery(imageUrls: product.imageUrls),
        Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                product.title,
                style: text.titleLarge?.copyWith(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 6),
              Text(
                formatUgx(variant?.price),
                style: text.titleLarge?.copyWith(
                  color: AppColors.navy,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 4),
              if (variant != null) _StockLabel(variant: variant),
              if (product.variants.length > 1) ...[
                const SizedBox(height: 16),
                Text(
                  'Choose an option',
                  style: text.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final option in product.variants)
                      ChoiceChip(
                        label: Text(option.label),
                        showCheckmark: false,
                        labelStyle: TextStyle(
                          fontSize: 13,
                          color: option.id == variant?.id
                              ? Colors.white
                              : AppColors.ink,
                        ),
                        selected: option.id == variant?.id,
                        onSelected: (_) => onSelect(option),
                      ),
                  ],
                ),
              ],
              if (product.description.isNotEmpty) ...[
                const SizedBox(height: 20),
                Text(
                  'Details',
                  style: text.titleMedium?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 6),
                Text(product.description, style: text.bodyMedium),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _Gallery extends StatefulWidget {
  const _Gallery({required this.imageUrls});

  final List<String> imageUrls;

  @override
  State<_Gallery> createState() => _GalleryState();
}

class _GalleryState extends State<_Gallery> {
  int _page = 0;

  @override
  Widget build(BuildContext context) {
    final urls = widget.imageUrls;
    return Container(
      color: AppColors.card,
      height: 300,
      child: urls.isEmpty
          ? const NetworkPicture(url: null)
          : Stack(
              children: [
                PageView.builder(
                  itemCount: urls.length,
                  onPageChanged: (page) => setState(() => _page = page),
                  itemBuilder: (_, index) => Padding(
                    padding: const EdgeInsets.all(16),
                    child: NetworkPicture(url: urls[index]),
                  ),
                ),
                if (urls.length > 1)
                  Positioned(
                    bottom: 10,
                    left: 0,
                    right: 0,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        for (var index = 0; index < urls.length; index++)
                          Container(
                            width: 8,
                            height: 8,
                            margin: const EdgeInsets.symmetric(horizontal: 3),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: index == _page
                                  ? AppColors.orange
                                  : AppColors.inputBorder,
                            ),
                          ),
                      ],
                    ),
                  ),
              ],
            ),
    );
  }
}

class _StockLabel extends StatelessWidget {
  const _StockLabel({required this.variant});

  final ProductVariant variant;

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(context).textTheme.bodySmall;
    if (!variant.inStock) {
      return Text(
        'Out of stock',
        style: style?.copyWith(color: AppColors.danger, fontWeight: FontWeight.w600),
      );
    }
    return Text(
      variant.stockQty <= 5 ? 'Only ${variant.stockQty} left' : 'In stock',
      style: style?.copyWith(color: AppColors.muted),
    );
  }
}

/// Add to cart, which turns into a quantity control once the item is in the cart.
class _BuyBar extends StatelessWidget {
  const _BuyBar({required this.product, required this.variant});

  final ProductDetail product;
  final ProductVariant? variant;

  @override
  Widget build(BuildContext context) {
    final selected = variant;
    final cart = context.watch<CartProvider>();
    final inCart = selected == null ? 0 : cart.quantityOf(selected.id);

    final Widget action;
    if (selected == null || !selected.inStock) {
      action = const FilledButton(onPressed: null, child: Text('Out of stock'));
    } else if (inCart == 0) {
      action = FilledButton.icon(
        onPressed: () => cart.add(product, selected),
        icon: const Icon(Icons.add_shopping_cart),
        label: const Text('Add to cart'),
      );
    } else {
      action = Row(
        children: [
          QuantityStepper(
            quantity: inCart,
            onDecrease: () => cart.decrease(selected.id),
            onIncrease: inCart < selected.stockQty
                ? () => cart.increase(selected.id)
                : null,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: FilledButton(
              onPressed: () => context.go('/cart'),
              child: const Text('View cart'),
            ),
          ),
        ],
      );
    }

    return Material(
      color: AppColors.card,
      elevation: 8,
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 10, 16, 10),
          child: action,
        ),
      ),
    );
  }
}
