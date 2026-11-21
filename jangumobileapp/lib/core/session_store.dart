import 'package:hive_ce_flutter/hive_flutter.dart';

/// Keeps the login tokens and the last fetched profile in Hive, so the user
/// stays logged in and sees their details straight away on the next launch.
class SessionStore {
  SessionStore(this._box);

  static const String _accessKey = 'access';
  static const String _refreshKey = 'refresh';
  static const String _profileKey = 'profile';

  final Box<dynamic> _box;

  String? get accessToken => _box.get(_accessKey) as String?;
  String? get refreshToken => _box.get(_refreshKey) as String?;
  bool get hasSession => refreshToken != null;

  Future<void> saveTokens({required String access, required String refresh}) {
    return _box.putAll({_accessKey: access, _refreshKey: refresh});
  }

  Map<String, dynamic>? get cachedProfile {
    final stored = _box.get(_profileKey);
    return stored is Map ? Map<String, dynamic>.from(stored) : null;
  }

  Future<void> saveProfile(Map<String, dynamic> profile) {
    return _box.put(_profileKey, profile);
  }

  Future<void> clear() => _box.clear();
}
