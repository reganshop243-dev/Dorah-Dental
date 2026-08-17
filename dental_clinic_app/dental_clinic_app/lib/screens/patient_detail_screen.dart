import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/colors.dart';

class PatientDetailScreen extends StatefulWidget {
  final int patientId;

  const PatientDetailScreen({Key? key, required this.patientId}) : super(key: key);

  @override
  _PatientDetailScreenState createState() => _PatientDetailScreenState();
}

class _PatientDetailScreenState extends State<PatientDetailScreen> {
  Map<String, dynamic> _patient = {};
  bool _isLoading = true;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _loadPatient();
  }

  Future<void> _loadPatient() async {
    try {
      final response = await ApiService.get('patients//');
      setState(() {
        _patient = response;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_patient['first_name'] != null
            ? ' '
            : 'Patient Details'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(Icons.edit),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Edit Patient Coming Soon')),
              );
            },
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
                          onPressed: _loadPatient,
                          child: Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : SingleChildScrollView(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    children: [
                      // Patient Info Card
                      Card(
                        child: Padding(
                          padding: EdgeInsets.all(16),
                          child: Column(
                            children: [
                              Row(
                                children: [
                                  CircleAvatar(
                                    radius: 40,
                                    backgroundColor: AppColors.primary,
                                    child: Text(
                                      _patient['first_name']?.substring(0, 1) ?? '?',
                                      style: TextStyle(
                                        fontSize: 32,
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ),
                                  SizedBox(width: 16),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          ' ',
                                          style: TextStyle(
                                            fontSize: 20,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                        Text(
                                          _patient['phone'] ?? 'No phone',
                                          style: TextStyle(color: AppColors.muted),
                                        ),
                                        if (_patient['email'] != null)
                                          Text(
                                            _patient['email'],
                                            style: TextStyle(color: AppColors.muted),
                                          ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      SizedBox(height: 16),
                      // Stats Row
                      Row(
                        children: [
                          Expanded(
                            child: _buildStatCard(
                              'Appointments',
                              _patient['appointments']?.length?.toString() ?? '0',
                              Icons.calendar_today,
                              Colors.blue,
                            ),
                          ),
                          SizedBox(width: 8),
                          Expanded(
                            child: _buildStatCard(
                              'Invoices',
                              _patient['invoices']?.length?.toString() ?? '0',
                              Icons.receipt,
                              Colors.green,
                            ),
                          ),
                          SizedBox(width: 8),
                          Expanded(
                            child: _buildStatCard(
                              'Balance',
                              'UGX ',
                              Icons.attach_money,
                              Colors.orange,
                            ),
                          ),
                        ],
                      ),
                      SizedBox(height: 16),
                      // Details
                      Card(
                        child: Padding(
                          padding: EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Patient Information',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              SizedBox(height: 12),
                              _buildInfoRow('Gender', _patient['gender'] ?? 'N/A'),
                              _buildInfoRow('Date of Birth', _patient['date_of_birth'] ?? 'N/A'),
                              _buildInfoRow('Age', _patient['age']?.toString() ?? 'N/A'),
                              _buildInfoRow('Address', _patient['address'] ?? 'N/A'),
                              _buildInfoRow('Registered', _patient['registered_at'] ?? 'N/A'),
                            ],
                          ),
                        ),
                      ),
                      SizedBox(height: 16),
                      // Quick Actions
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          _buildActionChip('Book Appointment', Icons.calendar_today, Colors.green),
                          _buildActionChip('Create Invoice', Icons.receipt, Colors.blue),
                          _buildActionChip('Dental Chart', Icons.medical_services, Colors.purple),
                          _buildActionChip('Add Image', Icons.image, Colors.orange),
                        ],
                      ),
                    ],
                  ),
                ),
    );
  }

  Widget _buildStatCard(String title, String value, IconData icon, Color color) {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(12),
        child: Column(
          children: [
            Icon(icon, color: color, size: 24),
            SizedBox(height: 4),
            Text(
              value,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            Text(
              title,
              style: TextStyle(fontSize: 11, color: AppColors.muted),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: TextStyle(color: AppColors.muted, fontWeight: FontWeight.w500),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(fontWeight: FontWeight.w500),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionChip(String label, IconData icon, Color color) {
    return ActionChip(
      label: Text(label),
      avatar: Icon(icon, size: 16, color: color),
      onPressed: () {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(' Coming Soon')),
        );
      },
      backgroundColor: color.withOpacity(0.1),
      side: BorderSide(color: color.withOpacity(0.3)),
    );
  }
}

