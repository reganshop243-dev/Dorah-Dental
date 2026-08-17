import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const String baseUrl = 'http://127.0.0.1:8000/api/';
  
  // Simple get - NO AUTH
  static Future<dynamic> get(String endpoint) async {
    final url = baseUrl + endpoint;
    print('📤 GET: ');
    
    try {
      final response = await http.get(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );
      return _handleResponse(response);
    } catch (e) {
      print('❌ Network error: ');
      throw Exception('Cannot connect to server');
    }
  }
  
  // Simple post - NO AUTH
  static Future<dynamic> post(String endpoint, Map<String, dynamic> data) async {
    final url = baseUrl + endpoint;
    print('📤 POST: ');
    
    try {
      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(data),
      );
      return _handleResponse(response);
    } catch (e) {
      print('❌ Network error: ');
      throw Exception('Cannot connect to server');
    }
  }
  
  // PUT method - for updates
  static Future<dynamic> put(String endpoint, Map<String, dynamic> data) async {
    final url = baseUrl + endpoint;
    print('📤 PUT: ');
    
    try {
      final response = await http.put(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(data),
      );
      return _handleResponse(response);
    } catch (e) {
      print('❌ Network error: ');
      throw Exception('Cannot connect to server');
    }
  }
  
  // DELETE method
  static Future<dynamic> delete(String endpoint) async {
    final url = baseUrl + endpoint;
    print('📤 DELETE: ');
    
    try {
      final response = await http.delete(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );
      return _handleResponse(response);
    } catch (e) {
      print('❌ Network error: ');
      throw Exception('Cannot connect to server');
    }
  }
  
  static dynamic _handleResponse(http.Response response) {
    print('📊 Status: ');
    print('📊 Body: ');
    
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) return {'success': true};
      try {
        return jsonDecode(response.body);
      } catch (e) {
        return {'error': 'Invalid response'};
      }
    }
    
    // Try to get error message from response
    try {
      final error = jsonDecode(response.body);
      throw Exception(error['error'] ?? error['message'] ?? 'Server error');
    } catch (e) {
      throw Exception('Server error: ');
    }
  }
  
  // Token methods (kept for compatibility)
  static Future<String?> getToken() async => null;
  static Future<void> setToken(String token) async {}
  static Future<void> clearToken() async {}
}
