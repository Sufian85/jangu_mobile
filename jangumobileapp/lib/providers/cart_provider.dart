import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:hive_ce_flutter/hive_flutter.dart';

import '../core/api_client.dart';
import '../models/cart_item.dart';
import '../models/product.dart';
import '../services/catalogue_api.dart';

/// The shopping cart. It lives in Hive on the device, so it survives restarts
/// and works without logging in.
class CartProvider extends ChangeNotifier {
  CartProvider(this._box) {
    for (final stored in _box.values) {
      final item = CartItem.fromMap(Map<String, dynamic>.from(stored as Map));
      _items[item.variantId] = item;
    }
  }

  final Box<dynamic> _box;
  final Map<int, CartItem> _items = {};

  /// Most recently added first.
  List<CartItem> get items {
    return _items.values.toList()..sort((a, b) => b.addedAt.compareTo(a.addedAt));
  }

  bool get isEmpty => _items.isEmpty;

  /// Number of units in the cart, which is what the badge on the cart tab shows.
  int get itemCount {
    return _items.values.fold(0, (sum, item) => sum + item.quantity);
  }

  /// Out-of-stock lines stay visible in the cart but don't count towards the total.
  double get subtotal {
    return _items.values
        .where((item) => item.isAvailable)
        .fold(0, (sum, item) => sum + item.lineTotal);
  }

  int quantityOf(int variantId) => _items[variantId]?.quantity ?? 0;

  /// Adds a product variant, never going above the available stock.
  void add(ProductDetail product, ProductVariant variant, {int quantity = 1}) {
    if (!variant.inStock) return;
    final current = quantityOf(variant.id);
    _save(CartItem(
      variantId: variant.id,
      productSlug: product.slug,
      title: product.title,
      brand: product.brand,
      variantLabel: variant.label,
      imageUrl: product.primaryImage,
      unitPrice: variant.price,
      stockQty: variant.stockQty,
      quantity: min(current + quantity, variant.stockQty),
      addedAt: _items[variant.id]?.addedAt ?? DateTime.now().millisecondsSinceEpoch,
    ));
  }

  void increase(int variantId) {
    final item = _items[variantId];
    if (item == null || !item.canIncrease) return;
    _save(item.copyWith(quantity: item.quantity + 1));
  }

  /// Takes one away, and removes the line when the last one goes.
  void decrease(int variantId) {
    final item = _items[variantId];
    if (item == null) return;
    if (item.quantity <= 1) {
      remove(variantId);
    } else {
      _save(item.copyWith(quantity: item.quantity - 1));
    }
  }

  void remove(int variantId) {
    if (_items.remove(variantId) == null) return;
    _box.delete(variantId);
    notifyListeners();
  }

  /// Puts a removed line back, for the Undo action.
  void restore(CartItem item) => _save(item);

  void clear() {
    _items.clear();
    _box.clear();
    notifyListeners();
  }

  /// Updates saved prices and stock from the server, since either may have
  /// changed since the item was added. Lines for products that no longer exist
  /// are dropped. If the phone is offline, the saved values are kept.
  Future<void> syncWithCatalogue(CatalogueApi api) async {
    final slugs = _items.values.map((item) => item.productSlug).toSet();
    for (final slug in slugs) {
      final lines = _items.values.where((item) => item.productSlug == slug).toList();
      try {
        final product = await api.fetchProduct(slug);
        final variants = {for (final variant in product.variants) variant.id: variant};
        for (final line in lines) {
          final variant = variants[line.variantId];
          if (variant == null) {
            _items.remove(line.variantId);
            _box.delete(line.variantId);
          } else {
            _store(line.copyWith(
              title: product.title,
              brand: product.brand,
              variantLabel: variant.label,
              imageUrl: product.primaryImage,
              unitPrice: variant.price,
              stockQty: variant.stockQty,
              // Keep at least one so a sold-out line stays visible as such.
              quantity: max(1, min(line.quantity, variant.stockQty)),
            ));
          }
        }
      } on ApiException catch (error) {
        if (error.statusCode == 404) {
          for (final line in lines) {
            _items.remove(line.variantId);
            _box.delete(line.variantId);
          }
        }
      }
    }
    notifyListeners();
  }

  void _save(CartItem item) {
    _store(item);
    notifyListeners();
  }

  void _store(CartItem item) {
    _items[item.variantId] = item;
    _box.put(item.variantId, item.toMap());
  }
}
