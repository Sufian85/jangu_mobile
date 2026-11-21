abstract final class AppConfig {
  /// Must end with a slash so relative paths like `products/` resolve under `/api/`.
  ///
  /// Point a build at another server without changing code, e.g. the Android
  /// emulator against a local backend:
  ///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://jangumobile.site/api/',
  );
}
