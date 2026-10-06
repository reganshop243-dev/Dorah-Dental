import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  static const String baseUrl = String.fromEnvironment(
    'DORAH_API_URL',
    defaultValue: 'https://dorah-dental-production.up.railway.app/api',
  );

  static String? token;
  static Map<String, dynamic>? patient;

  static bool get isLoggedIn => token != null;

  static Future<void> init() async {
    final p = await SharedPreferences.getInstance();
    token = p.getString('token');
    final raw = p.getString('patient');
    if (raw != null) patient = jsonDecode(raw);
  }

  static Future<Map<String, dynamic>> login(String identifier, String pin) async {
    final response = await http.post(
      Uri.parse('$baseUrl/mobile/login/'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'identifier': identifier, 'pin': pin}),
    );
    final data = _decode(response);
    if (response.statusCode != 200) throw Exception(data['error'] ?? 'Login failed');
    token = data['token'];
    patient = Map<String, dynamic>.from(data['patient'] ?? {});
    final p = await SharedPreferences.getInstance();
    await p.setString('token', token!);
    await p.setString('patient', jsonEncode(patient));
    return data;
  }

  static Future<void> logout() async {
    token = null;
    patient = null;
    final p = await SharedPreferences.getInstance();
    await p.remove('token');
    await p.remove('patient');
  }

  static Future<void> registerDeviceToken(String fcmToken) async {
    await post('/mobile/device-token/', {'token': fcmToken, 'platform': 'mobile'});
  }

  static Future<Map<String, dynamic>> dashboard() async => get('/mobile/dashboard/');
  static Future<List<dynamic>> notifications() async => (await get('/mobile/notifications/'))['results'] ?? [];
  static Future<List<dynamic>> messages() async => (await get('/mobile/messages/'))['results'] ?? [];
  static Future<Map<String, dynamic>> conversation(int id) async => get('/mobile/messages/$id/');
  static Future<Map<String, dynamic>> sendMessage(String subject, String body) async =>
      post('/mobile/messages/new/', {'subject': subject, 'body': body});
  static Future<Map<String, dynamic>> reply(int id, String body) async =>
      post('/mobile/messages/$id/reply/', {'body': body});
  static Future<void> markNotificationRead(int id) async => post('/mobile/notifications/$id/read/', {});

  static Map<String, String> _headers() => {
    'Content-Type': 'application/json',
    if (token != null) 'Authorization': 'Token $token',
  };

  static Future<Map<String, dynamic>> get(String path) async {
    final response = await http.get(Uri.parse('$baseUrl$path'), headers: _headers());
    final data = _decode(response);
    if (response.statusCode < 200 || response.statusCode >= 300) throw Exception(data['error'] ?? 'Request failed');
    return data;
  }

  static Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body) async {
    final response = await http.post(Uri.parse('$baseUrl$path'), headers: _headers(), body: jsonEncode(body));
    final data = _decode(response);
    if (response.statusCode < 200 || response.statusCode >= 300) throw Exception(data['error'] ?? 'Request failed');
    return data;
  }

  static Map<String, dynamic> _decode(http.Response response) {
    try { return Map<String, dynamic>.from(jsonDecode(response.body)); }
    catch (_) { return {'error': response.body.isNotEmpty ? response.body : 'Server error'}; }
  }
}
