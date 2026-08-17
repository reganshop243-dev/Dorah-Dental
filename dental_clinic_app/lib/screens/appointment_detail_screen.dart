import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/colors.dart';
import '../widgets/status_badge.dart';

class AppointmentDetailScreen extends StatefulWidget {
  final int appointmentId;

  const AppointmentDetailScreen({Key? key, required this.appointmentId}) : super(key: key);

  @override
  _AppointmentDetailScreenState createState() => _AppointmentDetailScreenState();
}

class _AppointmentDetailScreenState extends State<AppointmentDetailScreen> {
  Map<String, dynamic> _appointment = {};
  bool _isLoading = true;
  String _errorMessage = '';

  @override
  void initState() {
    super.initState();
    _loadAppointment();
  }

  Future<void> _loadAppointment() async {
    try {
      final response = await ApiService.get('appointments//');
      setState(() {
        _appointment = response;
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
        title: Text('Appointment Details'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(Icons.edit),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Edit Appointment Coming Soon')),
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
                          onPressed: _loadAppointment,
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
                      // Status Header
                      Container(
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
                                  _appointment['patient_name'] ?? 'Unknown Patient',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 20,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                Text(
                                  'ID: #',
                                  style: TextStyle(color: Colors.white70),
                                ),
                              ],
                            ),
                            StatusBadge(
                              label: _appointment['status'] ?? 'Unknown',
                              status: _appointment['status'] ?? 'unknown',
                            ),
                          ],
                        ),
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
                                'Appointment Details',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              SizedBox(height: 12),
                              _buildDetailRow('Date', _appointment['appointment_date'] ?? 'N/A'),
                              _buildDetailRow('Time', _appointment['appointment_time'] ?? 'N/A'),
                              _buildDetailRow('Doctor', _appointment['doctor_name'] ?? 'N/A'),
                              _buildDetailRow('Service', _appointment['service_name'] ?? 'N/A'),
                              _buildDetailRow('Status', _appointment['status'] ?? 'N/A'),
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
                          _buildActionChip('Check In', Icons.login, Colors.blue),
                          _buildActionChip('Start Treatment', Icons.medical_services, Colors.green),
                          _buildActionChip('Complete', Icons.check_circle, Colors.green),
                          _buildActionChip('Cancel', Icons.cancel, Colors.red),
                          _buildActionChip('Create Invoice', Icons.receipt, Colors.orange),
                        ],
                      ),
                      SizedBox(height: 16),
                      // Notes
                      if (_appointment['notes'] != null && _appointment['notes'] != '')
                        Card(
                          child: Padding(
                            padding: EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Notes',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                SizedBox(height: 8),
                                Text(_appointment['notes']),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 80,
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
