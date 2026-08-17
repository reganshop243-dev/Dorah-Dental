import 'package:dio/dio.dart';

class ApiClient {
  late Dio _dio;
  
  // ✅ The known working token
  static const String _token = '1f826f6de661a23673bd3443abbd93c3f85a5cf5';
  
  ApiClient() {
    _dio = Dio(BaseOptions(
      baseUrl: 'http://127.0.0.1:8000/api',
      connectTimeout: const Duration(seconds: 30),
      receiveTimeout: const Duration(seconds: 30),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ));
  }
  
  Dio get dio => _dio;
  
  // For authenticated requests
  void addToken() {
    _dio.options.headers['Authorization'] = 'Token ';
  }
  
  // For login (no token needed)
  void removeToken() {
    _dio.options.headers.remove('Authorization');
  }
}
