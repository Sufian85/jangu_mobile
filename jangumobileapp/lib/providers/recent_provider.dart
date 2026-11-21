import 'package:flutter/foundation.dart';
import 'package:hive_ce_flutter/hive_flutter.dart';

import '../models/product.dart';

/// Recently viewed products, newest first, remembered in Hive.
class RecentProvider extends ChangeNotifier {
  RecentProvider(this._box) {
    final stored = _box.get(_key);
    if (stored is List) {
      _items = [
        for (final row in stored)
          ProductSummary.fromJson(Map<String, dynamic>.from(row as Map)),
      ];
    }
  }

  static const String _key = 'items';
  static const int _limit = 15;

  final Box<dynamic> _box;
  List<ProductSummary> _items = const [];

  List<ProductSummary> get items => _items;

  void add(ProductSummary product) {
    _items = [
      product,
      ..._items.where((item) => item.id != product.id),
    ].take(_limit).toList();
    _box.put(_key, [for (final item in _items) item.toJson()]);
    notifyListeners();
  }
}
