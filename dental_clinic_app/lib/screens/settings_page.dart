import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/colors.dart';

class SettingsPage extends StatefulWidget {
  @override
  _SettingsPageState createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  Map<String, dynamic> _settings = {};
  bool _isLoading = true;
  String _errorMessage = '';
  bool _isEditing = false;

  final _businessNameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _addressController = TextEditingController();
  final _currencyController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    setState(() => _isLoading = true);
    try {
      final response = await ApiService.get('settings/');
      setState(() {
        _settings = response;
        _businessNameController.text = _settings['business_name'] ?? '';
        _phoneController.text = _settings['phone'] ?? '';
        _emailController.text = _settings['email'] ?? '';
        _addressController.text = _settings['address'] ?? '';
        _currencyController.text = _settings['currency'] ?? 'UGX';
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _saveSettings() async {
    setState(() => _isLoading = true);
    try {
      final data = {
        'business_name': _businessNameController.text.trim(),
        'phone': _phoneController.text.trim(),
        'email': _emailController.text.trim(),
        'address': _addressController.text.trim(),
        'currency': _currencyController.text.trim(),
      };
      await ApiService.put('settings/', data);
      setState(() => _isEditing = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Settings saved!'), backgroundColor: Colors.green),
      );
      _loadSettings();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: '), backgroundColor: Colors.red),
      );
    }
    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Icon(Icons.settings, color: Colors.white),
            SizedBox(width: 8),
            Text('Settings'),
          ],
        ),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          if (_isEditing)
            IconButton(
              icon: Icon(Icons.save),
              onPressed: _saveSettings,
            ),
          IconButton(
            icon: Icon(_isEditing ? Icons.close : Icons.edit),
            onPressed: () => setState(() => _isEditing = !_isEditing),
          ),
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadSettings,
          ),
        ],
      ),
      body: _isLoading
          ? Center(child: CircularProgressIndicator())
          : _errorMessage.isNotEmpty
              ? Center(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.error_outline, size: 64, color: Colors.red),
                        SizedBox(height: 16),
                        Text(_errorMessage),
                        SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: _loadSettings,
                          child: Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : ListView(
                  children: [
                    _buildSection('Company Information', [
                      _buildSettingItem(
                        'Business Name',
                        _businessNameController,
                        Icons.business,
                        _isEditing,
                      ),
                      _buildSettingItem(
                        'Phone',
                        _phoneController,
                        Icons.phone,
                        _isEditing,
                      ),
                      _buildSettingItem(
                        'Email',
                        _emailController,
                        Icons.email,
                        _isEditing,
                      ),
                      _buildSettingItem(
                        'Address',
                        _addressController,
                        Icons.location_on,
                        _isEditing,
                      ),
                      _buildSettingItem(
                        'Currency',
                        _currencyController,
                        Icons.attach_money,
                        _isEditing,
                      ),
                    ]),

                    _buildSection('User Management', [
                      ListTile(
                        leading: Icon(Icons.people, color: AppColors.primary),
                        title: Text('Manage Users'),
                        subtitle: Text('Add, edit, or remove users'),
                        trailing: Icon(Icons.chevron_right),
                        onTap: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('User Management Coming Soon')),
                          );
                        },
                      ),
                      ListTile(
                        leading: Icon(Icons.security, color: AppColors.primary),
                        title: Text('Roles & Permissions'),
                        subtitle: Text('Manage user roles'),
                        trailing: Icon(Icons.chevron_right),
                        onTap: () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text('Role Management Coming Soon')),
                          );
                        },
                      ),
                    ]),

                    _buildSection('System', [
                      ListTile(
                        leading: Icon(Icons.info, color: AppColors.primary),
                        title: Text('About'),
                        subtitle: Text('Version 1.0.0'),
                        trailing: Icon(Icons.chevron_right),
                        onTap: () {
                          showDialog(
                            context: context,
                            builder: (context) => AlertDialog(
                              title: Text('About'),
                              content: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.health_and_safety, size: 64, color: AppColors.primary),
                                  SizedBox(height: 16),
                                  Text(
                                    "Dora's Dental Gem",
                                    style: TextStyle(
                                      fontSize: 20,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  Text(
                                    'Clinic Management System',
                                    style: TextStyle(color: AppColors.muted),
                                  ),
                                  SizedBox(height: 8),
                                  Text('Version 1.0.0'),
                                  Text('Built with Flutter & Django'),
                                ],
                              ),
                              actions: [
                                TextButton(
                                  onPressed: () => Navigator.pop(context),
                                  child: Text('Close'),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
                      ListTile(
                        leading: Icon(Icons.logout, color: Colors.red),
                        title: Text(
                          'Logout',
                          style: TextStyle(color: Colors.red),
                        ),
                        trailing: Icon(Icons.chevron_right, color: Colors.red),
                        onTap: () async {
                          await ApiService.clearToken();
                          Navigator.pushReplacementNamed(context, '/login');
                        },
                      ),
                    ]),
                  ],
                ),
    );
  }

  Widget _buildSection(String title, List<Widget> children) {
    return Container(
      margin: EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Text(
              title,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: AppColors.muted,
              ),
            ),
          ),
          Card(
            margin: EdgeInsets.symmetric(horizontal: 8),
            child: Column(children: children),
          ),
        ],
      ),
    );
  }

  Widget _buildSettingItem(
    String label,
    TextEditingController controller,
    IconData icon,
    bool isEditing,
  ) {
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          Icon(icon, color: AppColors.primary, size: 20),
          SizedBox(width: 12),
          Expanded(
            child: isEditing
                ? TextFormField(
                    controller: controller,
                    decoration: InputDecoration(
                      labelText: label,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        label,
                        style: TextStyle(fontSize: 12, color: AppColors.muted),
                      ),
                      Text(
                        controller.text.isEmpty ? 'Not set' : controller.text,
                        style: TextStyle(fontWeight: FontWeight.w500),
                      ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}
