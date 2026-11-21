import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../core/formatters.dart';
import '../core/theme.dart';
import '../models/cart_item.dart';
import '../providers/cart_provider.dart';
import '../services/catalogue_api.dart';
import '../widgets/message_view.dart';
import '../widgets/network_picture.dart';
import '../widgets/quantity_stepper.dart';

class CartScreen extends StatefulWidget {
  const CartScreen({super.key});

  @override
  State<CartScreen> createState() => _CartScreenState();
}

class _CartScreenState extends State<CartScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _sync();
    });
  }

  Future<void> _sync() {
    return context.read<CartProvider>().syncWithCatalogue(context.read<CatalogueApi>());
  }

  Future<void> _confirmClear(CartProvider cart) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Empty your cart?'),
        content: const Text('This removes every item from your cart.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Keep items'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Empty cart'),
          ),
        ],
      ),
    );
    if (confirmed == true) cart.clear();
  }

  @override
  Widget build(BuildContext context) {
    final cart = context.watch<CartProvider>();
    final items = cart.items;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Your cart'),
        actions: [
          if (!cart.isEmpty)
            TextButton(
              onPressed: () => _confirmClear(cart),
              child: const Text('Empty'),
            ),
        ],
      ),
      body: cart.isEmpty
          ? MessageView(
              icon: Icons.shopping_cart_outlined,
              title: 'Your cart is empty',
              message: 'Products you add will show up here.',
              actionLabel: 'Start shopping',
              onAction: () => context.go('/'),
            )
          : Column(
              children: [
                Expanded(
                  child: RefreshIndicator(
                    onRefresh: _sync,
                    child: ListView.separated(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.all(16),
                      itemCount: items.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 10),
                      itemBuilder: (_, index) {
                        final item = items[index];
                        return _CartLine(key: ValueKey(item.variantId), item: item);
                      },
                    ),
                  ),
                ),
                _Summary(itemCount: cart.itemCount, subtotal: cart.subtotal),
              ],
            ),
    );
  }
}

class _CartLine extends StatelessWidget {
  const _CartLine({super.key, required this.item});

  final CartItem item;

  void _removeWithUndo(BuildContext context) {
    final cart = context.read<CartProvider>();
    final messenger = ScaffoldMessenger.of(context);
    cart.remove(item.variantId);
    messenger
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(
        content: Text('${item.title} removed'),
        action: SnackBarAction(label: 'Undo', onPressed: () => cart.restore(item)),
      ));
  }

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final cart = context.read<CartProvider>();

    return Dismissible(
      key: ValueKey('dismiss-${item.variantId}'),
      direction: DismissDirection.endToStart,
      onDismissed: (_) => _removeWithUndo(context),
      background: Container(
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 20),
        decoration: BoxDecoration(
          color: AppColors.danger,
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Icon(Icons.delete_outline, color: Colors.white),
      ),
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: () => context.push('/product/${item.productSlug}'),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SizedBox.square(
                  dimension: 76,
                  child: NetworkPicture(url: item.imageUrl),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: text.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
                      ),
                      Text(
                        item.variantLabel,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: text.bodySmall?.copyWith(color: AppColors.muted),
                      ),
                      const SizedBox(height: 4),
                      if (item.isAvailable)
                        Text(
                          formatUgx(item.unitPrice),
                          style: text.bodyMedium?.copyWith(
                            color: AppColors.navy,
                            fontWeight: FontWeight.w700,
                          ),
                        )
                      else
                        Text(
                          'Out of stock',
                          style: text.bodySmall?.copyWith(
                            color: AppColors.danger,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          QuantityStepper(
                            quantity: item.quantity,
                            onDecrease: item.quantity > 1
                                ? () => cart.decrease(item.variantId)
                                : () => _removeWithUndo(context),
                            onIncrease: item.canIncrease
                                ? () => cart.increase(item.variantId)
                                : null,
                          ),
                          const Spacer(),
                          IconButton(
                            icon: const Icon(Icons.delete_outline),
                            tooltip: 'Remove from cart',
                            color: AppColors.muted,
                            onPressed: () => _removeWithUndo(context),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _Summary extends StatelessWidget {
  const _Summary({required this.itemCount, required this.subtotal});

  final int itemCount;
  final double subtotal;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Material(
      color: AppColors.card,
      elevation: 8,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
        child: Row(
          children: [
            Expanded(
              child: Text(
                itemCount == 1 ? 'Total (1 item)' : 'Total ($itemCount items)',
                style: text.bodyMedium?.copyWith(color: AppColors.muted),
              ),
            ),
            Text(
              formatUgx(subtotal),
              style: text.titleMedium?.copyWith(
                color: AppColors.navy,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
