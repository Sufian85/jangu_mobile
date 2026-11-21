import '../core/api_client.dart';
import '../models/category.dart';
import '../models/product.dart';

class ProductPage {
  const ProductPage({
    required this.items,
    required this.totalCount,
    required this.hasMore,
  });

  final List<ProductSummary> items;
  final int totalCount;
  final bool hasMore;
}

class CatalogueApi {
  const CatalogueApi(this._client);

  final ApiClient _client;

  Future<List<Category>> fetchCategories() async {
    final data = await _client.get('categories/') as List;
    return [
      for (final row in data)
        Category.fromJson(Map<String, dynamic>.from(row as Map)),
    ];
  }

  /// One page of products, newest first. Pass [category] as a category slug.
  Future<ProductPage> fetchProducts({
    int page = 1,
    String? category,
    String? search,
  }) async {
    final data = await _client.get('products/', query: {
      'page': '$page',
      'category': ?category,
      if (search != null && search.isNotEmpty) 'search': search,
    }) as Map;

    return ProductPage(
      items: [
        for (final row in data['results'] as List)
          ProductSummary.fromJson(Map<String, dynamic>.from(row as Map)),
      ],
      totalCount: data['count'] as int,
      hasMore: data['next'] != null,
    );
  }

  Future<ProductDetail> fetchProduct(String slug) async {
    final data = await _client.get('products/$slug/') as Map;
    return ProductDetail.fromJson(Map<String, dynamic>.from(data));
  }
}
