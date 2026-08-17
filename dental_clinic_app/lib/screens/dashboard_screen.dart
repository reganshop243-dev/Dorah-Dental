import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../api/api_service.dart';
import '../utils/colors.dart';
import 'patients_page.dart';
import 'appointments_page.dart';
import 'services_page.dart';
import 'doctors_page.dart';
import 'billing_page.dart';
import 'inventory_page.dart';
import 'reports_page.dart';
import 'settings_page.dart';
import 'revenue_dashboard_page.dart';
import 'balance_sheet_page.dart';

class DashboardScreen extends StatefulWidget {
  @override
  _DashboardScreenState createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic> _data = {};
  bool _isLoading = true;
  String _errorMessage = '';
  int _selectedIndex = 0;

  // ✅ FIXED: Removed duplicates - only 11 pages (0-10)
  final List<Widget> _pages = [
    DashboardContent(),      // 0
    PatientsPage(),          // 1
    AppointmentsPage(),      // 2
    ServicesPage(),          // 3
    DoctorsPage(),           // 4
    BillingPage(),           // 5
    InventoryPage(),         // 6
    ReportsPage(),           // 7
    RevenueDashboardPage(),  // 8
    BalanceSheetPage(),      // 9
    SettingsPage(),          // 10
  ];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      print('📊 Loading dashboard data...');
      final response = await ApiService.get('stats/');
      print('✅ Dashboard data: $response');
      setState(() {
        _data = response;
        _isLoading = false;
      });
    } catch (e) {
      print('❌ Error loading dashboard: $e');
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
    // Navigate to login screen
    Navigator.pushReplacementNamed(context, '/login');
  }

  // ✅ FIXED: Logout is at index 11
  void _onDrawerItemSelected(int index) {
    // If logout (index 11), logout and return
    if (index == 11) {
      _logout();
      return;
    }
    
    // Otherwise navigate to the page
    setState(() {
      _selectedIndex = index;
    });
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text("Dora's Dental Gem"),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        elevation: 2,
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadData,
          ),
          IconButton(
            icon: Icon(Icons.logout),
            onPressed: _logout,
          ),
        ],
      ),
      drawer: AppDrawer(
        selectedIndex: _selectedIndex,
        onItemSelected: _onDrawerItemSelected,
      ),
      body: _pages[_selectedIndex],
    );
  }
}

// Dashboard Content Widget
class DashboardContent extends StatefulWidget {
  @override
  _DashboardContentState createState() => _DashboardContentState();
}

class _DashboardContentState extends State<DashboardContent> {
  Map<String, dynamic> _data = {};
  bool _isLoading = true;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      print('📊 Loading dashboard content...');
      final response = await ApiService.get('stats/');
      print('✅ Dashboard response: $response');
      setState(() {
        _data = response;
        _isLoading = false;
      });
    } catch (e) {
      print('❌ Error loading dashboard: $e');
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  void _navigateTo(int index) {
    final dashboardScreen = context.findAncestorStateOfType<_DashboardScreenState>();
    if (dashboardScreen != null) {
      dashboardScreen.setState(() {
        dashboardScreen._selectedIndex = index;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading dashboard...'),
          ],
        ),
      );
    }

    if (_errorMessage.isNotEmpty) {
      return Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.error_outline, size: 64, color: Colors.red),
              SizedBox(height: 16),
              Text(
                'Error loading data',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              SizedBox(height: 8),
              Text(
                _errorMessage,
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey[600]),
              ),
              SizedBox(height: 24),
              ElevatedButton(
                onPressed: _loadData,
                child: Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    // Get values with defaults
    final totalPatients = _data['total_patients'] ?? 0;
    final totalAppointments = _data['total_appointments'] ?? 0;
    final totalRevenue = _data['total_revenue'] ?? 0.0;
    final totalServices = _data['total_services'] ?? 0;
    final totalDoctors = _data['total_doctors'] ?? 0;

    return SingleChildScrollView(
      padding: EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Welcome Message
          Text(
            'Dashboard',
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: 4),
          Text(
            'Welcome to Dora\'s Dental Gem',
            style: TextStyle(
              fontSize: 14,
              color: AppColors.muted,
            ),
          ),
          SizedBox(height: 20),

          // Stats Row - 4 Cards
          GridView.count(
            shrinkWrap: true,
            physics: NeverScrollableScrollPhysics(),
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            childAspectRatio: 1.3,
            children: [
              _buildStatCard(
                'Total Patients',
                totalPatients.toString(),
                Icons.people,
                Colors.blue,
                () => _navigateTo(1),
              ),
              _buildStatCard(
                'Appointments',
                totalAppointments.toString(),
                Icons.calendar_today,
                Colors.green,
                () => _navigateTo(2),
              ),
              _buildStatCard(
                'Services',
                totalServices.toString(),
                Icons.medical_services,
                Colors.purple,
                () => _navigateTo(3),
              ),
              _buildStatCard(
                'Doctors',
                totalDoctors.toString(),
                Icons.person,
                Colors.orange,
                () => _navigateTo(4),
              ),
            ],
          ),

          SizedBox(height: 16),

          // Revenue Card
          Container(
            width: double.infinity,
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: AppColors.primaryGradient,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Total Revenue',
                      style: TextStyle(
                        color: Colors.white70,
                        fontSize: 14,
                      ),
                    ),
                    Text(
                      'UGX ${totalRevenue.toStringAsFixed(0)}',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
                Icon(
                  Icons.attach_money,
                  color: Colors.white.withOpacity(0.3),
                  size: 48,
                ),
              ],
            ),
          ),

          SizedBox(height: 16),

          // Quick Actions
          Container(
            width: double.infinity,
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Quick Actions',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 12),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _buildActionButton(
                      'New Patient',
                      Icons.person_add,
                      Colors.blue,
                      () => _navigateTo(1),
                    ),
                    _buildActionButton(
                      'New Appointment',
                      Icons.event,
                      Colors.green,
                      () => _navigateTo(2),
                    ),
                    _buildActionButton(
                      'New Invoice',
                      Icons.receipt,
                      Colors.orange,
                      () => _navigateTo(5),
                    ),
                    _buildActionButton(
                      'Revenue',
                      Icons.attach_money,
                      Colors.purple,
                      () => _navigateTo(8),
                    ),
                  ],
                ),
              ],
            ),
          ),

          SizedBox(height: 16),

          // Status Card
          Container(
            width: double.infinity,
            padding: EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.green[50],
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.green[300]!),
            ),
            child: Row(
              children: [
                Icon(Icons.check_circle, color: Colors.green, size: 24),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Connected to Django Backend',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Colors.green[800],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Card(
        elevation: 2,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        child: Container(
          padding: EdgeInsets.all(12),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 28, color: color),
              SizedBox(height: 8),
              Text(
                value,
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                title,
                style: TextStyle(
                  fontSize: 11,
                  color: Colors.grey[600],
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildActionButton(String label, IconData icon, Color color, VoidCallback onTap) {
    return ElevatedButton.icon(
      onPressed: onTap,
      icon: Icon(icon, size: 18),
      label: Text(label),
      style: ElevatedButton.styleFrom(
        backgroundColor: color.withOpacity(0.1),
        foregroundColor: color,
        side: BorderSide(color: color.withOpacity(0.3)),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
        padding: EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      ),
    );
  }
}

// AppDrawer Widget
class AppDrawer extends StatelessWidget {
  final int selectedIndex;
  final Function(int) onItemSelected;

  const AppDrawer({
    Key? key,
    required this.selectedIndex,
    required this.onItemSelected,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          DrawerHeader(
            decoration: BoxDecoration(
              gradient: AppColors.primaryGradient,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                Icon(Icons.health_and_safety, color: Colors.white, size: 40),
                SizedBox(height: 8),
                Text(
                  "Dora's Dental Gem",
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  'Clinic Management System',
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
          _buildDrawerItem(
            index: 0,
            icon: Icons.dashboard,
            title: 'Dashboard',
            isSelected: selectedIndex == 0,
          ),
          _buildDrawerItem(
            index: 1,
            icon: Icons.people,
            title: 'Patients',
            isSelected: selectedIndex == 1,
          ),
          _buildDrawerItem(
            index: 2,
            icon: Icons.calendar_today,
            title: 'Appointments',
            isSelected: selectedIndex == 2,
          ),
          _buildDrawerItem(
            index: 3,
            icon: Icons.medical_services,
            title: 'Services',
            isSelected: selectedIndex == 3,
          ),
          _buildDrawerItem(
            index: 4,
            icon: Icons.person,
            title: 'Doctors',
            isSelected: selectedIndex == 4,
          ),
          _buildDrawerItem(
            index: 5,
            icon: Icons.receipt,
            title: 'Billing',
            isSelected: selectedIndex == 5,
          ),
          _buildDrawerItem(
            index: 6,
            icon: Icons.inventory,
            title: 'Inventory',
            isSelected: selectedIndex == 6,
          ),
          _buildDrawerItem(
            index: 7,
            icon: Icons.bar_chart,
            title: 'Reports',
            isSelected: selectedIndex == 7,
          ),
          _buildDrawerItem(
            index: 8,
            icon: Icons.attach_money,
            title: 'Revenue Dashboard',
            isSelected: selectedIndex == 8,
          ),
          _buildDrawerItem(
            index: 9,
            icon: Icons.balance,
            title: 'Balance Sheet',
            isSelected: selectedIndex == 9,
          ),
          Divider(),
          _buildDrawerItem(
            index: 10,
            icon: Icons.settings,
            title: 'Settings',
            isSelected: selectedIndex == 10,
          ),
          _buildDrawerItem(
            index: 11,
            icon: Icons.logout,
            title: 'Logout',
            isSelected: false,
            iconColor: Colors.red,
          ),
        ],
      ),
    );
  }

  Widget _buildDrawerItem({
    required int index,
    required IconData icon,
    required String title,
    required bool isSelected,
    Color? iconColor,
  }) {
    return ListTile(
      leading: Icon(
        icon,
        color: isSelected ? AppColors.primary : (iconColor ?? Colors.grey[600]),
      ),
      title: Text(
        title,
        style: TextStyle(
          color: isSelected ? AppColors.primary : null,
          fontWeight: isSelected ? FontWeight.bold : null,
        ),
      ),
      tileColor: isSelected ? AppColors.primary.withOpacity(0.05) : null,
      onTap: () => onItemSelected(index),
    );
  }
}