import 'package:flutter/material.dart';
import '../services/api_service.dart';

class AuthProvider with ChangeNotifier {
  bool _isAuthenticated = false;
  Map<String, dynamic>? _user;

  bool get isAuthenticated => _isAuthenticated;
  Map<String, dynamic>? get user => _user;

  Future<void> login(String username, String password) async {
    try {
      final response = await ApiService.postPublic('login/', {
        'username': username,
        'password': password,
      });
      
      if (response['token'] != null) {
        await ApiService.saveToken(response['token']);
        _user = response['user'];
        _isAuthenticated = true;
        notifyListeners();
      } else {
        throw Exception('Invalid credentials');
      }
    } catch (e) {
      throw Exception('Login failed: $e');
    }
  }

  Future<void> logout() async {
    await ApiService.clearToken();
    _user = null;
    _isAuthenticated = false;
    notifyListeners();
  }

  Future<bool> checkAuth() async {
    final token = await ApiService.getToken();
    _isAuthenticated = token != null;
    notifyListeners();
    return _isAuthenticated;
  }
}