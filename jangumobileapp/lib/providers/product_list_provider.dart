import 'package:flutter/foundation.dart';

import '../core/api_client.dart';
import '../models/product.dart';
import '../services/catalogue_api.dart';

/// A product list that loads one page at a time as the user scrolls. Each list
/// screen creates its own, optionally limited to a category or a search term.
class ProductListProvider extends ChangeNotifier {
  ProductListProvider(this._api, {this.categorySlug, this.search});

  final CatalogueApi _api;
  final String? categorySlug;
  final String? search;

  List<ProductSummary> items = const [];
  int totalCount = 0;
  bool isLoading = false;
  bool isLoadingMore = false;
  bool hasMore = false;
  String? error;
  int _page = 0;

  Future<void> refresh() async {
    isLoading = true;
    error = null;
    notifyListeners();

    try {
      final page = await _fetch(1);
      items = page.items;
      totalCount = page.totalCount;
      hasMore = page.hasMore;
      _page = 1;
    } on ApiException catch (exception) {
      error = exception.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<void> loadMore() async {
    if (isLoading || isLoadingMore || !hasMore) return;
    isLoadingMore = true;
    notifyListeners();

    try {
      final page = await _fetch(_page + 1);
      items = [...items, ...page.items];
      totalCount = page.totalCount;
      hasMore = page.hasMore;
      _page += 1;
    } on ApiException {
      // Leave the list as it is. Scrolling to the bottom again retries.
    } finally {
      isLoadingMore = false;
      notifyListeners();
    }
  }

  Future<ProductPage> _fetch(int page) {
    return _api.fetchProducts(page: page, category: categorySlug, search: search);
  }
}
