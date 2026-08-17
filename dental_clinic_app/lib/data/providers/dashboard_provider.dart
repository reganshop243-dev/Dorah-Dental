import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import '../models/appointment_model.dart';
import '../models/dashboard_stats_model.dart';

class DashboardProvider extends ChangeNotifier {
  static const String token = '1f826f6de661a23673bd3443abbd93c3f85a5cf5';
  
  DashboardStats? _stats;
  List<Appointment> _appointments = [];
  bool _isLoading = false;
  String? _error;
  
  DashboardStats? get stats => _stats;
  List<Appointment> get appointments => _appointments;
  bool get isLoading => _isLoading;
  String? get error => _error;
  
  Future<void> loadDashboardData() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    
    try {
      final url = Uri.parse('http://127.0.0.1:8000/api/admin/stats/');
      
      final response = await http.get(
        url,
        headers: {
          'Authorization': 'Token 1f826f6de661a23673bd3443abbd93c3f85a5cf5',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );
      
      print('📊 Status: ');
      print('📊 Body: ');
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _stats = DashboardStats.fromJson(data);
        
        // Load appointments
        final apptUrl = Uri.parse('http://127.0.0.1:8000/api/admin/appointments/');
        final apptResponse = await http.get(
          apptUrl,
          headers: {
            'Authorization': 'Token 1f826f6de661a23673bd3443abbd93c3f85a5cf5',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
        );
        
        if (apptResponse.statusCode == 200) {
          final apptData = jsonDecode(apptResponse.body);
          final List<dynamic> results = apptData['results'] ?? [];
          _appointments = results.map((json) => Appointment.fromJson(json)).toList();
          print('✅ Loaded  appointments');
        }
      }
      
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _isLoading = false;
      _error = e.toString();
      print('❌ Error: ');
      notifyListeners();
    }
  }
}
