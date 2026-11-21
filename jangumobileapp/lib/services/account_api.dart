import '../core/api_client.dart';
import '../models/user_profile.dart';

class AuthTokens {
  const AuthTokens({required this.access, required this.refresh});

  factory AuthTokens.fromJson(Map<dynamic, dynamic> json) {
    return AuthTokens(
      access: json['access'] as String,
      refresh: json['refresh'] as String,
    );
  }

  final String access;
  final String refresh;
}

class AccountApi {
  const AccountApi(this._client);

  final ApiClient _client;

  Future<AuthTokens> login({
    required String phone,
    required String password,
  }) async {
    final data = await _client.post(
      'auth/login/',
      body: {'phone': phone, 'password': password},
    ) as Map;
    return AuthTokens.fromJson(data);
  }

  Future<AuthTokens> register({
    required String phone,
    required String password,
    required String firstName,
    required String lastName,
  }) async {
    final data = await _client.post(
      'auth/register/',
      body: {
        'phone': phone,
        'password': password,
        'first_name': firstName,
        'last_name': lastName,
      },
    ) as Map;
    return AuthTokens.fromJson(data);
  }

  Future<void> logout(String refreshToken) {
    return _client.post(
      'auth/logout/',
      body: {'refresh': refreshToken},
      auth: true,
    );
  }

  Future<Map<String, dynamic>> fetchProfile() async {
    final data = await _client.get('auth/me/', auth: true) as Map;
    return Map<String, dynamic>.from(data);
  }

  Future<List<Address>> fetchAddresses() async {
    final data = await _client.get('auth/addresses/', auth: true) as List;
    return [
      for (final row in data)
        Address.fromJson(Map<String, dynamic>.from(row as Map)),
    ];
  }
}
