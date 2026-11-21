import 'dart:convert';

import 'package:http/http.dart' as http;

import 'config.dart';
import 'session_store.dart';

class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.fieldErrors = const {}});

  /// Reads the backend's error shape: `{"errors": {...}, "status_code": 400}`,
  /// where `errors` holds either `detail` or a list of messages per field.
  factory ApiException.fromResponse(int statusCode, dynamic body) {
    final errors = body is Map ? (body['errors'] ?? body) : null;
    final fieldErrors = <String, String>{};
    String? message;

    if (errors is Map) {
      errors.forEach((key, value) {
        final text = value is List && value.isNotEmpty && value.first is String
            ? value.first as String
            : value is String
                ? value
                : null;
        if (text == null || key == 'code') return;
        if (key == 'detail' || key == 'non_field_errors') {
          message = text;
        } else {
          fieldErrors['$key'] = text;
        }
      });
    }

    return ApiException(
      message ??
          (fieldErrors.isNotEmpty
              ? 'Please check the highlighted fields.'
              : 'Something went wrong. Please try again.'),
      statusCode: statusCode,
      fieldErrors: fieldErrors,
    );
  }

  final String message;
  final int? statusCode;
  final Map<String, String> fieldErrors;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient(this._session, {http.Client? httpClient})
      : _http = httpClient ?? http.Client();

  static const Duration _timeout = Duration(seconds: 25);

  final SessionStore _session;
  final http.Client _http;

  /// Called when the refresh token is rejected, meaning the user must log in again.
  void Function()? onSessionExpired;

  // Refresh tokens rotate and the old one is blacklisted, so two refreshes at
  // once would log the user out. Parallel requests share this one instead.
  Future<bool>? _refreshing;

  Future<dynamic> get(
    String path, {
    Map<String, String>? query,
    bool auth = false,
  }) {
    return _send('GET', path, query: query, auth: auth);
  }

  Future<dynamic> post(String path, {Object? body, bool auth = false}) {
    return _send('POST', path, body: body, auth: auth);
  }

  Future<dynamic> _send(
    String method,
    String path, {
    Map<String, String>? query,
    Object? body,
    required bool auth,
  }) async {
    var response = await _request(method, path, query, body, auth);
    if (auth && response.statusCode == 401 && await _refreshTokens()) {
      response = await _request(method, path, query, body, auth);
    }
    final decoded = _decode(response);
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return decoded;
    }
    throw ApiException.fromResponse(response.statusCode, decoded);
  }

  Future<http.Response> _request(
    String method,
    String path,
    Map<String, String>? query,
    Object? body,
    bool auth,
  ) async {
    var uri = Uri.parse(AppConfig.apiBaseUrl).resolve(path);
    if (query != null && query.isNotEmpty) {
      uri = uri.replace(queryParameters: query);
    }

    final request = http.Request(method, uri)
      ..headers['Accept'] = 'application/json';
    if (body != null) {
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode(body);
    }
    final token = _session.accessToken;
    if (auth && token != null) {
      request.headers['Authorization'] = 'Bearer $token';
    }

    try {
      final streamed = await _http.send(request).timeout(_timeout);
      return await http.Response.fromStream(streamed).timeout(_timeout);
    } on Exception {
      throw ApiException(
        'Could not reach the server. Check your connection and try again.',
      );
    }
  }

  dynamic _decode(http.Response response) {
    if (response.bodyBytes.isEmpty) return null;
    try {
      // The API sends JSON without a charset, and http would then assume latin1.
      return jsonDecode(utf8.decode(response.bodyBytes));
    } on FormatException {
      return null;
    }
  }

  Future<bool> _refreshTokens() {
    return _refreshing ??= _doRefresh().whenComplete(() => _refreshing = null);
  }

  Future<bool> _doRefresh() async {
    final refresh = _session.refreshToken;
    if (refresh == null) return false;

    final http.Response response;
    try {
      response = await _request(
        'POST',
        'auth/refresh/',
        null,
        {'refresh': refresh},
        false,
      );
    } on ApiException {
      // Offline is not the same as logged out, so keep the session.
      return false;
    }

    final decoded = _decode(response);
    if (response.statusCode == 200 && decoded is Map) {
      await _session.saveTokens(
        access: decoded['access'] as String,
        refresh: (decoded['refresh'] as String?) ?? refresh,
      );
      return true;
    }
    if (response.statusCode == 400 || response.statusCode == 401) {
      onSessionExpired?.call();
    }
    return false;
  }
}
