import 'package:flutter/material.dart';
import 'dart:convert';
import '../services/api_client.dart';
import '../models/user_model.dart';
import '../../core/utils/token_manager.dart';
import '../../core/constants/api_constants.dart';

class AuthProvider extends ChangeNotifier {
  final ApiClient _apiClient = ApiClient();
  
  UserModel? _user;
  bool _isLoading = false;
  String? _error;
  
  UserModel? get user => _user;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isAuthenticated => _user != null;
  
  AuthProvider() {
    _loadUser();
  }
  
  Future<void> _loadUser() async {
    final userData = await TokenManager.getUser();
    if (userData != null && userData.isNotEmpty) {
      try {
        _user = UserModel.fromJson(jsonDecode(userData));
        notifyListeners();
      } catch (e) {}
    }
  }
  
  Future<bool> login(String username, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    
    try {
      // ✅ Remove token before login
      _apiClient.removeToken();
      
      final response = await _apiClient.dio.post(
        ApiConstants.login,
        data: {'username': username, 'password': password},
      );
      
      if (response.statusCode == 200) {
        final data = response.data;
        final token = data['token'] as String;
        final userData = data['user'];
        
        await TokenManager.setToken(token);
        await TokenManager.setUser(jsonEncode(userData));
        
        _user = UserModel.fromJson(userData);
        _isLoading = false;
        notifyListeners();
        return true;
      }
      
      _isLoading = false;
      _error = 'Login failed';
      notifyListeners();
      return false;
      
    } catch (e) {
      _isLoading = false;
      _error = 'Connection error';
      notifyListeners();
      return false;
    }
  }
  
  Future<void> logout() async {
    await TokenManager.clearToken();
    _user = null;
    notifyListeners();
  }
}
