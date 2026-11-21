double? _parsePrice(Object? value) => double.tryParse('$value');

/// A product as shown in lists. Also stored in Hive for recently viewed items.
class ProductSummary {
  const ProductSummary({
    required this.id,
    required this.slug,
    required this.title,
    required this.brand,
    required this.inStock,
    this.imageUrl,
    this.priceFrom,
  });

  factory ProductSummary.fromJson(Map<String, dynamic> json) {
    return ProductSummary(
      id: json['id'] as int,
      slug: json['slug'] as String,
      title: json['title'] as String,
      brand: json['brand'] as String,
      imageUrl: json['primary_image'] as String?,
      priceFrom: _parsePrice(json['price_from']),
      inStock: json['in_stock'] as bool,
    );
  }

  final int id;
  final String slug;
  final String title;
  final String brand;
  final String? imageUrl;
  final double? priceFrom;
  final bool inStock;

  Map<String, dynamic> toJson() => {
        'id': id,
        'slug': slug,
        'title': title,
        'brand': brand,
        'primary_image': imageUrl,
        'price_from': priceFrom,
        'in_stock': inStock,
      };
}

class ProductVariant {
  const ProductVariant({
    required this.id,
    required this.sku,
    required this.attributes,
    required this.price,
    required this.stockQty,
  });

  factory ProductVariant.fromJson(Map<String, dynamic> json) {
    return ProductVariant(
      id: json['id'] as int,
      sku: json['sku'] as String,
      attributes: Map<String, dynamic>.from(json['attributes'] as Map? ?? {}),
      price: _parsePrice(json['price']) ?? 0,
      stockQty: json['stock_qty'] as int,
    );
  }

  // The API returns attributes in Postgres's key order, not the order they were
  // entered, so use the same fixed display order as the website.
  static const List<String> _attributeOrder = [
    'processor',
    'ram',
    'storage',
    'size',
    'connectivity',
    'color',
  ];

  final int id;
  final String sku;
  final Map<String, dynamic> attributes;
  final double price;
  final int stockQty;

  bool get inStock => stockQty > 0;

  /// For example `128GB / Black`, or `Standard` when there are no attributes.
  String get label {
    int rank(String key) {
      final index = _attributeOrder.indexOf(key);
      return index == -1 ? _attributeOrder.length : index;
    }

    final keys = attributes.keys.toList()
      ..sort((a, b) {
        final byRank = rank(a).compareTo(rank(b));
        return byRank != 0 ? byRank : a.compareTo(b);
      });
    final parts = [
      for (final key in keys)
        if (attributes[key] != null && attributes[key] != '') '${attributes[key]}',
    ];
    return parts.isEmpty ? 'Standard' : parts.join(' / ');
  }
}

class ProductDetail {
  const ProductDetail({
    required this.id,
    required this.slug,
    required this.title,
    required this.brand,
    required this.description,
    required this.variants,
    required this.imageUrls,
  });

  factory ProductDetail.fromJson(Map<String, dynamic> json) {
    final images = [
      for (final image in json['images'] as List? ?? const [])
        Map<String, dynamic>.from(image as Map),
    ]..sort((a, b) {
        final byPrimary =
            (b['is_primary'] == true ? 1 : 0) - (a['is_primary'] == true ? 1 : 0);
        return byPrimary != 0
            ? byPrimary
            : (a['sort_order'] as int).compareTo(b['sort_order'] as int);
      });

    return ProductDetail(
      id: json['id'] as int,
      slug: json['slug'] as String,
      title: json['title'] as String,
      brand: json['brand'] as String,
      description: (json['description'] as String?) ?? '',
      variants: [
        for (final variant in json['variants'] as List? ?? const [])
          ProductVariant.fromJson(Map<String, dynamic>.from(variant as Map)),
      ],
      imageUrls: [for (final image in images) image['image'] as String],
    );
  }

  final int id;
  final String slug;
  final String title;
  final String brand;
  final String description;
  final List<ProductVariant> variants;
  final List<String> imageUrls;

  String? get primaryImage => imageUrls.isEmpty ? null : imageUrls.first;

  ProductSummary toSummary() {
    final prices = variants.map((variant) => variant.price);
    return ProductSummary(
      id: id,
      slug: slug,
      title: title,
      brand: brand,
      imageUrl: primaryImage,
      priceFrom: prices.isEmpty ? null : prices.reduce((a, b) => a < b ? a : b),
      inStock: variants.any((variant) => variant.inStock),
    );
  }
}
