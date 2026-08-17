import 'package:flutter/material.dart';
import 'screens/login_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/patients_page.dart';
import 'screens/appointments_page.dart';
import 'screens/services_page.dart';
import 'screens/doctors_page.dart';
import 'screens/billing_page.dart';
import 'screens/inventory_page.dart';
import 'screens/reports_page.dart';
import 'screens/settings_page.dart';
import 'screens/patient_detail_screen.dart';
import 'api/api_service.dart';
import 'utils/colors.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "Dora's Dental Gem",
      theme: ThemeData(
        primaryColor: AppColors.primary,
        scaffoldBackgroundColor: AppColors.cardBg,
        appBarTheme: AppBarTheme(
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          elevation: 2,
          centerTitle: false,
        ),
        cardTheme: CardThemeData(
          elevation: 2,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        inputDecorationTheme: InputDecorationTheme(
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          filled: true,
          fillColor: Colors.white,
        ),
        elevatedButtonTheme: ElevatedButtonThemeData(
          style: ElevatedButton.styleFrom(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
            ),
            padding: EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          ),
        ),
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      debugShowCheckedModeBanner: false,
      initialRoute: '/',
      routes: {
        '/': (context) => FutureBuilder<bool>(
          future: _checkAuth(),
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return Scaffold(body: Center(child: CircularProgressIndicator()));
            }
            if (snapshot.hasData && snapshot.data == true) {
              return DashboardScreen();
            }
            return LoginScreen();
          },
        ),
        '/login': (context) => LoginScreen(),
        '/dashboard': (context) => DashboardScreen(),
        '/patients': (context) => PatientsPage(),
        '/appointments': (context) => AppointmentsPage(),
        '/services': (context) => ServicesPage(),
        '/doctors': (context) => DoctorsPage(),
        '/billing': (context) => BillingPage(),
        '/inventory': (context) => InventoryPage(),
        '/reports': (context) => ReportsPage(),
        '/settings': (context) => SettingsPage(),
      },
    );
  }

  Future<bool> _checkAuth() async {
    try {
      final token = await ApiService.getToken();
      return token != null && token.isNotEmpty;
    } catch (e) {
      return false;
    }
  }
}
