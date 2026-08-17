import 'package:flutter/material.dart';
import '../utils/colors.dart';

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
            onTap: () {
              onItemSelected(0);
              Navigator.pop(context);
            },
          ),
          _buildDrawerItem(
            index: 1,
            icon: Icons.people,
            title: 'Patients',
            isSelected: selectedIndex == 1,
            onTap: () {
              onItemSelected(1);
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Patients page coming soon!')),
              );
            },
          ),
          _buildDrawerItem(
            index: 2,
            icon: Icons.calendar_today,
            title: 'Appointments',
            isSelected: selectedIndex == 2,
            onTap: () {
              onItemSelected(2);
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Appointments page coming soon!')),
              );
            },
          ),
          _buildDrawerItem(
            index: 3,
            icon: Icons.medical_services,
            title: 'Services',
            isSelected: selectedIndex == 3,
            onTap: () {
              onItemSelected(3);
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Services page coming soon!')),
              );
            },
          ),
          _buildDrawerItem(
            index: 4,
            icon: Icons.person,
            title: 'Doctors',
            isSelected: selectedIndex == 4,
            onTap: () {
              onItemSelected(4);
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Doctors page coming soon!')),
              );
            },
          ),
          _buildDrawerItem(
            index: 5,
            icon: Icons.receipt,
            title: 'Billing',
            isSelected: selectedIndex == 5,
            onTap: () {
              onItemSelected(5);
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Billing page coming soon!')),
              );
            },
          ),
          _buildDrawerItem(
            index: 6,
            icon: Icons.inventory,
            title: 'Inventory',
            isSelected: selectedIndex == 6,
            onTap: () {
              onItemSelected(6);
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Inventory page coming soon!')),
              );
            },
          ),
          _buildDrawerItem(
            index: 7,
            icon: Icons.bar_chart,
            title: 'Reports',
            isSelected: selectedIndex == 7,
            onTap: () {
              onItemSelected(7);
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Reports page coming soon!')),
              );
            },
          ),
          Divider(),
          _buildDrawerItem(
            index: 8,
            icon: Icons.settings,
            title: 'Settings',
            isSelected: selectedIndex == 8,
            onTap: () {
              onItemSelected(8);
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Settings page coming soon!')),
              );
            },
          ),
          _buildDrawerItem(
            index: 9,
            icon: Icons.logout,
            title: 'Logout',
            isSelected: false,
            iconColor: Colors.red,
            onTap: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Logging out...')),
              );
            },
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
    required VoidCallback onTap,
    Color? iconColor,
  }) {
    return ListTile(
      leading: Icon(
        icon,
        color: isSelected ? AppColors.primary : (iconColor ?? AppColors.muted),
      ),
      title: Text(
        title,
        style: TextStyle(
          color: isSelected ? AppColors.primary : null,
          fontWeight: isSelected ? FontWeight.bold : null,
        ),
      ),
      tileColor: isSelected ? AppColors.primary.withOpacity(0.05) : null,
      onTap: onTap,
    );
  }
}
