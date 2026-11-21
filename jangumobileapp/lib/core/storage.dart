import 'package:hive_ce_flutter/hive_flutter.dart';

/// The Hive boxes the app keeps on the device. They hold plain maps, so no
/// generated type adapters are needed.
abstract final class AppBoxes {
  static const String session = 'session';
  static const String cart = 'cart';
  static const String recent = 'recent';

  static Future<void> open() async {
    await Future.wait([
      Hive.openBox<dynamic>(session),
      Hive.openBox<dynamic>(cart),
      Hive.openBox<dynamic>(recent),
    ]);
  }
}
