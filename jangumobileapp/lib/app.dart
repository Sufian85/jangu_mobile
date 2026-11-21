import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:hive_ce_flutter/hive_flutter.dart';
import 'package:provider/provider.dart';

import 'core/api_client.dart';
import 'core/router.dart';
import 'core/session_store.dart';
import 'core/storage.dart';
import 'core/theme.dart';
import 'providers/auth_provider.dart';
import 'providers/cart_provider.dart';
import 'providers/catalogue_provider.dart';
import 'providers/recent_provider.dart';
import 'services/account_api.dart';
import 'services/catalogue_api.dart';

class JanguApp extends StatelessWidget {
  const JanguApp({super.key, required this.session, required this.api});

  final SessionStore session;
  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    final catalogueApi = CatalogueApi(api);
    return MultiProvider(
      providers: [
        Provider<CatalogueApi>.value(value: catalogueApi),
        ChangeNotifierProvider(
          create: (_) => AuthProvider(AccountApi(api), session, api),
        ),
        ChangeNotifierProvider(
          create: (_) => CatalogueProvider(catalogueApi)..load(),
        ),
        ChangeNotifierProvider(
          create: (_) => CartProvider(Hive.box<dynamic>(AppBoxes.cart)),
        ),
        ChangeNotifierProvider(
          create: (_) => RecentProvider(Hive.box<dynamic>(AppBoxes.recent)),
        ),
      ],
      child: const _RoutedApp(),
    );
  }
}

class _RoutedApp extends StatefulWidget {
  const _RoutedApp();

  @override
  State<_RoutedApp> createState() => _RoutedAppState();
}

class _RoutedAppState extends State<_RoutedApp> {
  // Built once so a theme or provider rebuild never resets navigation.
  late final GoRouter _router;

  @override
  void initState() {
    super.initState();
    _router = createRouter(context.read<AuthProvider>());
  }

  @override
  void dispose() {
    _router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Jangu Mobile',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      routerConfig: _router,
    );
  }
}
