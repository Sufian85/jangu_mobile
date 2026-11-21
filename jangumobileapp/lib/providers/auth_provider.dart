import 'dart:async';

import 'package:flutter/foundation.dart';

import '../core/api_client.dart';
import '../core/session_store.dart';
import '../models/user_profile.dart';
import '../services/account_api.dart';

class AuthProvider extends ChangeNotifier {
  AuthProvider(this._api, this._session, ApiClient client) {
    client.onSessionExpired = _clearSession;
    final cached = _session.cachedProfile;
    if (cached != null) profile = UserProfile.fromJson(cached);
  }

  final AccountApi _api;
  final SessionStore _session;

  UserProfile? profile;
  List<Address> addresses = const [];
  bool isLoadingProfile = false;
  String? profileError;

  bool get isLoggedIn => _session.hasSession;

  Future<void> login({required String phone, required String password}) async {
    final tokens = await _api.login(phone: phone, password: password);
    await _startSession(tokens);
  }

  Future<void> register({
    required String phone,
    required String password,
    required String firstName,
    required String lastName,
  }) async {
    final tokens = await _api.register(
      phone: phone,
      password: password,
      firstName: firstName,
      lastName: lastName,
    );
    await _startSession(tokens);
  }

  Future<void> _startSession(AuthTokens tokens) async {
    await _session.saveTokens(access: tokens.access, refresh: tokens.refresh);
    notifyListeners();
    // Not awaited, so the login screen can move on while the profile loads.
    unawaited(loadProfile());
  }

  /// Fetches the logged-in user's details and saved addresses from the server.
  Future<void> loadProfile() async {
    if (!isLoggedIn || isLoadingProfile) return;
    isLoadingProfile = true;
    profileError = null;
    notifyListeners();

    try {
      final results = await Future.wait<Object>([
        _api.fetchProfile(),
        _api.fetchAddresses(),
      ]);
      final json = results[0] as Map<String, dynamic>;
      profile = UserProfile.fromJson(json);
      addresses = results[1] as List<Address>;
      await _session.saveProfile(json);
    } on ApiException catch (error) {
      // An expired session has already logged the user out, so there is nothing
      // to show an error on.
      profileError = isLoggedIn ? error.message : null;
    } finally {
      isLoadingProfile = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    final refresh = _session.refreshToken;
    if (refresh != null) {
      try {
        await _api.logout(refresh);
      } on ApiException {
        // Still log out on this device if the server can't be reached. The
        // token then simply expires by itself.
      }
    }
    await _clearSession();
  }

  Future<void> _clearSession() async {
    await _session.clear();
    profile = null;
    addresses = const [];
    profileError = null;
    notifyListeners();
  }
}
