import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../screens/app_shell.dart';
import '../screens/cart_screen.dart';
import '../screens/categories_screen.dart';
import '../screens/home_screen.dart';
import '../screens/login_screen.dart';
import '../screens/product_detail_screen.dart';
import '../screens/product_list_screen.dart';
import '../screens/profile_screen.dart';
import '../screens/register_screen.dart';

GoRouter createRouter(AuthProvider auth) {
  final rootKey = GlobalKey<NavigatorState>();

  return GoRouter(
    navigatorKey: rootKey,
    initialLocation: '/',
    refreshListenable: auth,
    redirect: (context, state) {
      final path = state.matchedLocation;
      if (auth.isLoggedIn && (path == '/login' || path == '/register')) {
        return '/profile';
      }
      return null;
    },
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => AppShell(shell: shell),
        branches: [
          StatefulShellBranch(routes: [
            GoRoute(path: '/', builder: (_, _) => const HomeScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/categories', builder: (_, _) => const CategoriesScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/cart', builder: (_, _) => const CartScreen()),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(path: '/profile', builder: (_, _) => const ProfileScreen()),
          ]),
        ],
      ),
      // These open over the tabs, so Back returns to where the user was.
      GoRoute(
        path: '/products',
        parentNavigatorKey: rootKey,
        builder: (_, state) {
          final query = state.uri.queryParameters['q'];
          return ProductListScreen(
            key: ValueKey('products-$query'),
            title: query == null ? 'All products' : 'Results for “$query”',
            search: query,
          );
        },
      ),
      GoRoute(
        path: '/categories/:slug',
        parentNavigatorKey: rootKey,
        builder: (_, state) {
          final slug = state.pathParameters['slug']!;
          return ProductListScreen(
            key: ValueKey('category-$slug'),
            title: state.uri.queryParameters['name'] ?? 'Products',
            categorySlug: slug,
          );
        },
      ),
      GoRoute(
        path: '/product/:slug',
        parentNavigatorKey: rootKey,
        builder: (_, state) {
          final slug = state.pathParameters['slug']!;
          return ProductDetailScreen(key: ValueKey(slug), slug: slug);
        },
      ),
      GoRoute(
        path: '/login',
        parentNavigatorKey: rootKey,
        builder: (_, _) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        parentNavigatorKey: rootKey,
        builder: (_, _) => const RegisterScreen(),
      ),
    ],
  );
}
