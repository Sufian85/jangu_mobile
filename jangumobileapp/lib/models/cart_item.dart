/// One line in the cart, stored in Hive under its variant id.
class CartItem {
  const CartItem({
    required this.variantId,
    required this.productSlug,
    required this.title,
    required this.brand,
    required this.variantLabel,
    required this.unitPrice,
    required this.stockQty,
    required this.quantity,
    required this.addedAt,
    this.imageUrl,
  });

  factory CartItem.fromMap(Map<String, dynamic> map) {
    return CartItem(
      variantId: map['variant_id'] as int,
      productSlug: map['product_slug'] as String,
      title: map['title'] as String,
      brand: map['brand'] as String,
      variantLabel: map['variant_label'] as String,
      imageUrl: map['image_url'] as String?,
      unitPrice: (map['unit_price'] as num).toDouble(),
      stockQty: map['stock_qty'] as int,
      quantity: map['quantity'] as int,
      addedAt: map['added_at'] as int,
    );
  }

  final int variantId;
  final String productSlug;
  final String title;
  final String brand;
  final String variantLabel;
  final String? imageUrl;
  final double unitPrice;
  final int stockQty;
  final int quantity;
  final int addedAt;

  bool get isAvailable => stockQty > 0;
  bool get canIncrease => quantity < stockQty;
  double get lineTotal => unitPrice * quantity;

  CartItem copyWith({
    String? title,
    String? brand,
    String? variantLabel,
    String? imageUrl,
    double? unitPrice,
    int? stockQty,
    int? quantity,
  }) {
    return CartItem(
      variantId: variantId,
      productSlug: productSlug,
      title: title ?? this.title,
      brand: brand ?? this.brand,
      variantLabel: variantLabel ?? this.variantLabel,
      imageUrl: imageUrl ?? this.imageUrl,
      unitPrice: unitPrice ?? this.unitPrice,
      stockQty: stockQty ?? this.stockQty,
      quantity: quantity ?? this.quantity,
      addedAt: addedAt,
    );
  }

  Map<String, dynamic> toMap() => {
        'variant_id': variantId,
        'product_slug': productSlug,
        'title': title,
        'brand': brand,
        'variant_label': variantLabel,
        'image_url': imageUrl,
        'unit_price': unitPrice,
        'stock_qty': stockQty,
        'quantity': quantity,
        'added_at': addedAt,
      };
}
