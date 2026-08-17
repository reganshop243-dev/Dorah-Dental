import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/colors.dart';
import 'appointment_detail_screen.dart';
import 'appointment_add_screen.dart';

class AppointmentsPage extends StatefulWidget {
  @override
  _AppointmentsPageState createState() => _AppointmentsPageState();
}

class _AppointmentsPageState extends State<AppointmentsPage> {
  List<dynamic> _appointments = [];
  bool _isLoading = true;
  String _errorMessage = '';
  String _statusFilter = '';
  String _dateFilter = '';
  bool _isCalendarView = false;

  @override
  void initState() {
    super.initState();
    _loadAppointments();
  }

  Future<void> _loadAppointments() async {
    setState(() => _isLoading = true);
    try {
      String url = 'appointments/';
      List<String> params = [];
      if (_statusFilter.isNotEmpty) params.add('status=');
      if (_dateFilter.isNotEmpty) params.add('date=');
      if (params.isNotEmpty) url += '?' + params.join('&');

      final response = await ApiService.get(url);
      
      // Handle different response formats
      if (response is List) {
        _appointments = response;
      } else if (response is Map && response.containsKey('results')) {
        _appointments = response['results'] ?? [];
      } else if (response is Map && response.containsKey('data')) {
        _appointments = response['data'] ?? [];
      } else if (response is Map) {
        // Try to find any list in the response
        var found = false;
        for (var key in response.keys) {
          if (response[key] is List) {
            _appointments = response[key];
            found = true;
            break;
          }
        }
        if (!found) _appointments = [];
      } else {
        _appointments = [];
      }
      _isLoading = false;
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Color _getStatusColor(String status) {
    switch (status?.toLowerCase()) {
      case 'scheduled': return Colors.blue;
      case 'checked_in': return Colors.orange;
      case 'in_progress': return Colors.purple;
      case 'completed': return Colors.green;
      case 'cancelled': return Colors.red;
      case 'no_show': return Colors.grey;
      default: return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Icon(Icons.calendar_today, color: Colors.white),
            SizedBox(width: 8),
            Text('Appointments'),
          ],
        ),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(_isCalendarView ? Icons.list : Icons.calendar_month),
            onPressed: () => setState(() => _isCalendarView = !_isCalendarView),
          ),
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadAppointments,
          ),
        ],
      ),
      body: Column(
        children: [
          Container(
            padding: EdgeInsets.all(12),
            color: Colors.white,
            child: Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<String>(
                    value: _statusFilter.isEmpty ? null : _statusFilter,
                    decoration: InputDecoration(
                      hintText: 'Status',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12),
                    ),
                    items: [
                      DropdownMenuItem(value: '', child: Text('All Status')),
                      DropdownMenuItem(value: 'scheduled', child: Text('Scheduled')),
                      DropdownMenuItem(value: 'checked_in', child: Text('Checked In')),
                      DropdownMenuItem(value: 'in_progress', child: Text('In Progress')),
                      DropdownMenuItem(value: 'completed', child: Text('Completed')),
                      DropdownMenuItem(value: 'cancelled', child: Text('Cancelled')),
                    ],
                    onChanged: (value) {
                      setState(() => _statusFilter = value ?? '');
                      _loadAppointments();
                    },
                  ),
                ),
                SizedBox(width: 8),
                Expanded(
                  child: TextFormField(
                    decoration: InputDecoration(
                      hintText: 'Date',
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12),
                      suffixIcon: Icon(Icons.calendar_today),
                    ),
                    readOnly: true,
                    onTap: () async {
                      final date = await showDatePicker(
                        context: context,
                        initialDate: DateTime.now(),
                        firstDate: DateTime(2020),
                        lastDate: DateTime(2030),
                      );
                      if (date != null) {
                        setState(() => _dateFilter = date.toString().split(' ')[0]);
                        _loadAppointments();
                      }
                    },
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: AppColors.cardBg,
            child: Text(
              ' appointments',
              style: TextStyle(color: AppColors.muted),
            ),
          ),
          Expanded(
            child: _isLoading
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
                                onPressed: _loadAppointments,
                                child: Text('Retry'),
                              ),
                            ],
                          ),
                        ),
                      )
                    : _appointments.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.calendar_today, size: 64, color: AppColors.muted),
                                SizedBox(height: 16),
                                Text('No Appointments', style: TextStyle(fontSize: 18)),
                                SizedBox(height: 8),
                                Text('Schedule your first appointment', style: TextStyle(color: AppColors.muted)),
                                SizedBox(height: 16),
                                ElevatedButton(
                                  onPressed: () => _navigateToAddAppointment(),
                                  child: Text('Book Appointment'),
                                ),
                              ],
                            ),
                          )
                        : ListView.builder(
                            padding: EdgeInsets.all(8),
                            itemCount: _appointments.length,
                            itemBuilder: (context, index) {
                              final appt = _appointments[index];
                              return Card(
                                elevation: 1,
                                margin: EdgeInsets.only(bottom: 8),
                                child: ListTile(
                                  leading: Container(
                                    width: 12,
                                    height: 12,
                                    decoration: BoxDecoration(
                                      color: _getStatusColor(appt['status']),
                                      shape: BoxShape.circle,
                                    ),
                                  ),
                                  title: Text(
                                    appt['patient_name'] ?? 'Unknown Patient',
                                    style: TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                  subtitle: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(' '),
                                      Text(' - '),
                                    ],
                                  ),
                                  trailing: Container(
                                    padding: EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: _getStatusColor(appt['status']).withOpacity(0.15),
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: Text(
                                      appt['status'] ?? 'Unknown',
                                      style: TextStyle(
                                        color: _getStatusColor(appt['status']),
                                        fontSize: 12,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ),
                                  onTap: () => _navigateToAppointmentDetail(appt['id']),
                                ),
                              );
                            },
                          ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _navigateToAddAppointment,
        backgroundColor: AppColors.primary,
        child: Icon(Icons.add),
      ),
    );
  }

  void _navigateToAppointmentDetail(int id) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => AppointmentDetailScreen(appointmentId: id)),
    ).then((_) => _loadAppointments());
  }

  void _navigateToAddAppointment() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => AppointmentAddScreen()),
    ).then((_) => _loadAppointments());
  }
}
