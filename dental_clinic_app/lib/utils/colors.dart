import 'package:flutter/material.dart';

class AppColors {
  static const Color primary = Color(0xFF1a5276);
  static const Color primaryLight = Color(0xFF2980b9);
  static const Color accent = Color(0xFF2ecc71);
  static const Color warning = Color(0xFFf39c12);
  static const Color danger = Color(0xFFe74c3c);
  static const Color dark = Color(0xFF0a1a2e);
  static const Color cardBg = Color(0xFFf8f9fa);
  static const Color muted = Color(0xFF6c757d);
  static const Color border = Color(0xFFdee2e6);
  
  static const LinearGradient primaryGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF1a5276), Color(0xFF2980b9)],
  );
}
