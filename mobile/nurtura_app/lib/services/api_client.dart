import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

/// A failed API call, with a caregiver-readable [message] and any
/// per-field validation errors returned by the backend.
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.fieldErrors = const {}});

  final String message;
  final int? statusCode;
  final Map<String, List<String>> fieldErrors;

  /// The error for one field, or null if there isn't one.
  String? field(String name) {
    final errors = fieldErrors[name];
    return errors == null || errors.isEmpty ? null : errors.join(' ');
  }

  @override
  String toString() => message;
}

/// JSON client for the Django REST API, adding the auth token when set.
class ApiClient {
  ApiClient({required this.baseUrl, http.Client? httpClient})
      : _http = httpClient ?? http.Client();

  static const timeout = Duration(seconds: 20);

  final String baseUrl;
  final http.Client _http;

  /// Auth token sent as `Authorization: Token <token>` when set.
  String? token;

  Future<dynamic> get(String path, {Map<String, String>? query}) =>
      _send('GET', path, query: query);

  Future<dynamic> post(String path, [Object? body]) =>
      _send('POST', path, body: body);

  Future<dynamic> _send(
    String method,
    String path, {
    Map<String, String>? query,
    Object? body,
  }) async {
    var uri = Uri.parse('$baseUrl$path');
    if (query != null && query.isNotEmpty) {
      uri = uri.replace(queryParameters: query);
    }
    final request = http.Request(method, uri)
      ..headers['Accept'] = 'application/json';
    if (token != null) request.headers['Authorization'] = 'Token $token';
    if (body != null) {
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode(body);
    }

    final http.Response response;
    try {
      final streamed = await _http.send(request).timeout(timeout);
      response = await http.Response.fromStream(streamed).timeout(timeout);
    } on TimeoutException {
      throw ApiException(
        'The server took too long to respond. Please try again.',
      );
    } catch (_) {
      throw ApiException(
        "Can't reach the Nurtura server. Check your connection and try again.",
      );
    }

    // DRF doesn't send a charset, and package:http would assume Latin-1.
    final text = utf8.decode(response.bodyBytes);
    final data = text.isEmpty ? null : _tryDecode(text);
    if (response.statusCode >= 200 && response.statusCode < 300) return data;
    throw _errorFor(response.statusCode, data);
  }

  static dynamic _tryDecode(String text) {
    try {
      return jsonDecode(text);
    } on FormatException {
      return null;
    }
  }

  static ApiException _errorFor(int status, dynamic data) {
    final fields = <String, List<String>>{};
    String? detail;
    if (data is Map) {
      for (final entry in data.entries) {
        final key = entry.key.toString();
        final value = entry.value;
        if (key == 'detail') {
          detail = value.toString();
        } else if (value is List) {
          fields[key] = value.map((e) => e.toString()).toList();
        } else if (value is String) {
          fields[key] = [value];
        }
      }
    }

    if (status == 429) {
      final seconds = RegExp(r'(\d+) second').firstMatch(detail ?? '')?.group(1);
      return ApiException(
        seconds == null
            ? 'Too many attempts. Please wait a minute and try again.'
            : 'Too many attempts. Please wait $seconds seconds and try again.',
        statusCode: status,
      );
    }
    if (status == 401) {
      return ApiException(
        'Your session has ended. Please log in again.',
        statusCode: status,
      );
    }
    if (status >= 500) {
      return ApiException(
        'The server had a problem ($status). Please try again shortly.',
        statusCode: status,
      );
    }

    final general = fields.remove('non_field_errors');
    final message = general?.join(' ') ??
        detail ??
        (fields.isNotEmpty
            ? 'Please check the highlighted fields.'
            : 'Something went wrong ($status). Please try again.');
    return ApiException(message, statusCode: status, fieldErrors: fields);
  }
}
