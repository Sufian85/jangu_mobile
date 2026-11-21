// Flutter's foundation library has its own `Category`, which would clash with ours.
import 'package:flutter/foundation.dart' show ChangeNotifier;

import '../core/api_client.dart';
import '../models/category.dart';
import '../models/product.dart';
import '../services/catalogue_api.dart';

/// What the home and categories screens need: categories, and the newest products.
class CatalogueProvider extends ChangeNotifier {
  CatalogueProvider(this._api);

  final CatalogueApi _api;

  List<Category> categories = const [];
  List<ProductSummary> latestProducts = const [];
  bool isLoading = false;
  String? error;

  bool get hasData => categories.isNotEmpty || latestProducts.isNotEmpty;

  Future<void> load() async {
    isLoading = true;
    error = null;
    notifyListeners();

    try {
      final results = await Future.wait<Object>([
        _api.fetchCategories(),
        _api.fetchProducts(),
      ]);
      categories = [
        for (final category in results[0] as List<Category>)
          if (category.parentId == null) category,
      ];
      latestProducts = (results[1] as ProductPage).items;
    } on ApiException catch (exception) {
      error = exception.message;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }
}
