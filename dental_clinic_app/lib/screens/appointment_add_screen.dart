import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/colors.dart';

class AppointmentAddScreen extends StatefulWidget {
  @override
  _AppointmentAddScreenState createState() => _AppointmentAddScreenState();
}

class _AppointmentAddScreenState extends State<AppointmentAddScreen> {
  final _formKey = GlobalKey<FormState>();
  final _patientSearchController = TextEditingController();
  final _notesController = TextEditingController();
  final _notificationEmailController = TextEditingController();
  final _notificationPhoneController = TextEditingController();

  int? _selectedPatientId;
  String? _selectedPatientName;
  int? _selectedDoctorId;
  int? _selectedServiceId;
  DateTime? _appointmentDate;
  TimeOfDay? _appointmentTime;
  String _status = 'scheduled';
  bool _sendReminder = true;

  List<dynamic> _patients = [];
  List<dynamic> _doctors = [];
  List<dynamic> _services = [];
  bool _isLoading = false;
  bool _isSearching = false;

  @override
  void initState() {
    super.initState();
    _loadDropdownData();
  }

  Future<void> _loadDropdownData() async {
    setState(() => _isLoading = true);
    try {
      final patients = await ApiService.get('patients/');
      final doctors = await ApiService.get('doctors/');
      final services = await ApiService.get('services/');

      setState(() {
        _patients = patients['results'] ?? patients;
        _doctors = doctors['results'] ?? doctors;
        _services = services['results'] ?? services;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error loading data: '), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _searchPatients(String query) async {
    if (query.length < 2) return;
    setState(() => _isSearching = true);
    try {
      final response = await ApiService.get('patients/?q=');
      setState(() {
        _patients = response['results'] ?? response;
        _isSearching = false;
      });
    } catch (e) {
      setState(() => _isSearching = false);
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_selectedPatientId == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Please select a patient'), backgroundColor: Colors.orange),
      );
      return;
    }
    if (_appointmentDate == null || _appointmentTime == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Please select date and time'), backgroundColor: Colors.orange),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final data = {
        'patient': _selectedPatientId,
        'doctor': _selectedDoctorId,
        'service': _selectedServiceId,
        'appointment_date': _appointmentDate!.toString().split(' ')[0],
        'appointment_time': _appointmentTime!.format(context),
        'status': _status,
        'notes': _notesController.text.trim(),
        'notification_email': _notificationEmailController.text.trim(),
        'notification_phone': _notificationPhoneController.text.trim(),
        'send_reminder': _sendReminder,
      };

      await ApiService.post('appointments/', data);
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Appointment created successfully!'), backgroundColor: Colors.green),
      );
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
        title: Text('New Appointment'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
      ),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: EdgeInsets.all(16),
          child: Column(
            children: [
              // Patient Search
              Container(
                margin: EdgeInsets.only(bottom: 16),
                padding: EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.cardBg,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Patient *', style: TextStyle(fontWeight: FontWeight.bold)),
                    SizedBox(height: 8),
                    TextFormField(
                      controller: _patientSearchController,
                      decoration: InputDecoration(
                        hintText: 'Search patient...',
                        prefixIcon: Icon(Icons.search),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                        filled: true,
                        fillColor: Colors.white,
                        suffixIcon: _isSearching
                            ? SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : null,
                      ),
                      onChanged: (value) => _searchPatients(value),
                    ),
                    if (_selectedPatientName != null)
                      Container(
                        margin: EdgeInsets.only(top: 8),
                        padding: EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.green.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.green),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Expanded(child: Text(_selectedPatientName!)),
                            IconButton(
                              icon: Icon(Icons.close, size: 16),
                              onPressed: () {
                                setState(() {
                                  _selectedPatientId = null;
                                  _selectedPatientName = null;
                                  _patientSearchController.clear();
                                });
                              },
                            ),
                          ],
                        ),
                      ),
                    if (_patients.isNotEmpty && _selectedPatientName == null)
                      Container(
                        margin: EdgeInsets.only(top: 8),
                        constraints: BoxConstraints(maxHeight: 200),
                        child: ListView.builder(
                          shrinkWrap: true,
                          itemCount: _patients.length,
                          itemBuilder: (context, index) {
                            final patient = _patients[index];
                            return ListTile(
                              dense: true,
                              title: Text(' '),
                              subtitle: Text(patient['phone'] ?? ''),
                              onTap: () {
                                setState(() {
                                  _selectedPatientId = patient['id'];
                                  _selectedPatientName = ' ';
                                  _patientSearchController.text = _selectedPatientName!;
                                  _patients = [];
                                });
                              },
                            );
                          },
                        ),
                      ),
                  ],
                ),
              ),

              // Appointment Details
              Container(
                margin: EdgeInsets.only(bottom: 16),
                padding: EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.cardBg,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Appointment Details', style: TextStyle(fontWeight: FontWeight.bold)),
                    SizedBox(height: 12),
                    DropdownButtonFormField<int>(
                      decoration: InputDecoration(
                        labelText: 'Doctor *',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                        filled: true,
                        fillColor: Colors.white,
                      ),
                      items: _doctors.map((doctor) {
                        return DropdownMenuItem<int>(
                          value: doctor['id'],
                          child: Text(doctor['display_name'] ?? doctor['name'] ?? 'Unknown'),
                        );
                      }).toList(),
                      onChanged: (value) => setState(() => _selectedDoctorId = value),
                      validator: (value) => value == null ? 'Please select a doctor' : null,
                    ),
                    SizedBox(height: 12),
                    DropdownButtonFormField<int>(
                      decoration: InputDecoration(
                        labelText: 'Service *',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                        filled: true,
                        fillColor: Colors.white,
                      ),
                      items: _services.map((service) {
                        return DropdownMenuItem<int>(
                          value: service['id'],
                          child: Text(service['name'] ?? 'Unknown'),
                        );
                      }).toList(),
                      onChanged: (value) => setState(() => _selectedServiceId = value),
                      validator: (value) => value == null ? 'Please select a service' : null,
                    ),
                    SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            decoration: InputDecoration(
                              labelText: 'Date *',
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                              filled: true,
                              fillColor: Colors.white,
                              suffixIcon: Icon(Icons.calendar_today),
                            ),
                            readOnly: true,
                            onTap: () async {
                              final date = await showDatePicker(
                                context: context,
                                initialDate: DateTime.now().add(Duration(days: 1)),
                                firstDate: DateTime.now(),
                                lastDate: DateTime.now().add(Duration(days: 365)),
                              );
                              if (date != null) {
                                setState(() => _appointmentDate = date);
                              }
                            },
                            validator: (value) => _appointmentDate == null ? 'Please select a date' : null,
                          ),
                        ),
                        SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            decoration: InputDecoration(
                              labelText: 'Time *',
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                              filled: true,
                              fillColor: Colors.white,
                              suffixIcon: Icon(Icons.access_time),
                            ),
                            readOnly: true,
                            onTap: () async {
                              final time = await showTimePicker(
                                context: context,
                                initialTime: TimeOfDay.now(),
                              );
                              if (time != null) {
                                setState(() => _appointmentTime = time);
                              }
                            },
                            validator: (value) => _appointmentTime == null ? 'Please select a time' : null,
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: _status,
                      decoration: InputDecoration(
                        labelText: 'Status',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                        filled: true,
                        fillColor: Colors.white,
                      ),
                      items: [
                        DropdownMenuItem<String>(value: 'scheduled', child: Text('Scheduled')),
                        DropdownMenuItem<String>(value: 'checked_in', child: Text('Checked In')),
                        DropdownMenuItem<String>(value: 'in_progress', child: Text('In Progress')),
                        DropdownMenuItem<String>(value: 'completed', child: Text('Completed')),
                        DropdownMenuItem<String>(value: 'cancelled', child: Text('Cancelled')),
                      ],
                      onChanged: (value) => setState(() => _status = value!),
                    ),
                    SizedBox(height: 12),
                    TextFormField(
                      controller: _notesController,
                      decoration: InputDecoration(
                        labelText: 'Notes',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                        filled: true,
                        fillColor: Colors.white,
                      ),
                      maxLines: 3,
                    ),
                  ],
                ),
              ),

              // Notifications
              Container(
                margin: EdgeInsets.only(bottom: 16),
                padding: EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.cardBg,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.notifications, color: AppColors.primary),
                        SizedBox(width: 8),
                        Text('Reminders', style: TextStyle(fontWeight: FontWeight.bold)),
                      ],
                    ),
                    SizedBox(height: 12),
                    TextFormField(
                      controller: _notificationEmailController,
                      decoration: InputDecoration(
                        labelText: 'Notification Email',
                        hintText: 'Leave blank to use patient\'s email',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                        filled: true,
                        fillColor: Colors.white,
                      ),
                    ),
                    SizedBox(height: 12),
                    TextFormField(
                      controller: _notificationPhoneController,
                      decoration: InputDecoration(
                        labelText: 'Notification Phone',
                        hintText: 'Leave blank to use patient\'s phone',
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(8),
                        ),
                        filled: true,
                        fillColor: Colors.white,
                      ),
                    ),
                    SizedBox(height: 12),
                    SwitchListTile(
                      title: Text('Send Reminder'),
                      subtitle: Text('Send SMS confirmation to patient'),
                      value: _sendReminder,
                      onChanged: (value) => setState(() => _sendReminder = value),
                      activeColor: AppColors.primary,
                    ),
                  ],
                ),
              ),

              Row(
                children: [
                  Expanded(
                    child: ElevatedButton(
                      onPressed: _isLoading ? null : () => Navigator.pop(context),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.grey,
                      ),
                      child: Text('Cancel'),
                    ),
                  ),
                  SizedBox(width: 16),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: _isLoading ? null : _submit,
                      child: _isLoading
                          ? SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                              ),
                            )
                          : Text('Create Appointment'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
