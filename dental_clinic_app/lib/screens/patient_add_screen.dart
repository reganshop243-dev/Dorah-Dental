import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/colors.dart';

class PatientAddScreen extends StatefulWidget {
  @override
  _PatientAddScreenState createState() => _PatientAddScreenState();
}

class _PatientAddScreenState extends State<PatientAddScreen> {
  final _formKey = GlobalKey<FormState>();
  final _firstNameController = TextEditingController();
  final _lastNameController = TextEditingController();
  final _phoneController = TextEditingController();
  final _emailController = TextEditingController();
  final _addressController = TextEditingController();
  final _dateOfBirthController = TextEditingController();
  final _ageYearsController = TextEditingController();
  final _nextOfKinController = TextEditingController();
  final _nextOfKinContactController = TextEditingController();
  final _allergiesController = TextEditingController();
  final _currentMedicationsController = TextEditingController();
  final _reasonForVisitController = TextEditingController();
  final _discomfortDetailsController = TextEditingController();
  final _surgeryDetailsController = TextEditingController();
  final _lastDentalVisitController = TextEditingController();
  final _registeredAtController = TextEditingController();

  String _gender = 'M';
  String _underPhysician = 'no';
  String _dentalDiscomfort = 'no';
  String _previousSurgery = 'no';
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _registeredAtController.text = DateTime.now().toString().split(' ')[0];
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      final data = {
        'first_name': _firstNameController.text.trim(),
        'last_name': _lastNameController.text.trim(),
        'phone': _phoneController.text.trim(),
        'email': _emailController.text.trim(),
        'address': _addressController.text.trim(),
        'gender': _gender,
        'date_of_birth': _dateOfBirthController.text.isNotEmpty ? _dateOfBirthController.text : null,
        'age_years': _ageYearsController.text.isNotEmpty ? int.parse(_ageYearsController.text) : null,
        'next_of_kin': _nextOfKinController.text.trim(),
        'next_of_kin_contact': _nextOfKinContactController.text.trim(),
        'allergies': _allergiesController.text.trim(),
        'current_medications': _currentMedicationsController.text.trim(),
        'reason_for_visit': _reasonForVisitController.text.trim(),
        'under_physician': _underPhysician,
        'dental_discomfort': _dentalDiscomfort,
        'discomfort_details': _discomfortDetailsController.text.trim(),
        'previous_surgery': _previousSurgery,
        'surgery_details': _surgeryDetailsController.text.trim(),
        'last_dental_visit': _lastDentalVisitController.text.isNotEmpty ? _lastDentalVisitController.text : null,
        'registered_at': _registeredAtController.text.isNotEmpty ? _registeredAtController.text : null,
        'is_active': true,
      };

      final response = await ApiService.post('patients/', data);
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Patient registered successfully!'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: '),
          backgroundColor: Colors.red,
        ),
      );
    }

    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Add Patient'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
      ),
      body: Form(
        key: _formKey,
        child: SingleChildScrollView(
          padding: EdgeInsets.all(16),
          child: Column(
            children: [
              // Personal Information
              _buildSection('Personal Information', Icons.person, [
                _buildTextField(_firstNameController, 'First Name *', true),
                _buildTextField(_lastNameController, 'Last Name *', true),
                _buildDateField(_dateOfBirthController, 'Date of Birth'),
                _buildTextField(_ageYearsController, 'Age in Years', false, TextInputType.number),
                _buildGenderSelector(),
              ]),

              // Contact Information
              _buildSection('Contact Information', Icons.phone, [
                _buildTextField(_phoneController, 'Phone Number *', true, TextInputType.phone),
                _buildTextField(_emailController, 'Email Address', false, TextInputType.emailAddress),
                _buildTextField(_addressController, 'Address', false),
              ]),

              // Emergency Contact
              _buildSection('Emergency Contact', Icons.emergency, [
                _buildTextField(_nextOfKinController, 'Next of Kin Name', false),
                _buildTextField(_nextOfKinContactController, 'Next of Kin Contact', false, TextInputType.phone),
              ]),

              // Medical History
              _buildSection('Medical History', Icons.medical_services, [
                _buildRadioSelector('Under Physician', _underPhysician, (val) => setState(() => _underPhysician = val!), ['no', 'yes']),
                _buildTextField(_allergiesController, 'Allergies', false),
                _buildTextField(_currentMedicationsController, 'Current Medications', false),
              ]),

              // Dental History
              _buildSection('Dental History', Icons.medical_services, [
                _buildTextField(_reasonForVisitController, 'Reason for Visit *', true),
                _buildRadioSelector('Dental Discomfort', _dentalDiscomfort, (val) => setState(() => _dentalDiscomfort = val!), ['no', 'yes']),
                if (_dentalDiscomfort == 'yes')
                  _buildTextField(_discomfortDetailsController, 'Discomfort Details', false),
                _buildRadioSelector('Previous Surgery', _previousSurgery, (val) => setState(() => _previousSurgery = val!), ['no', 'yes']),
                if (_previousSurgery == 'yes')
                  _buildTextField(_surgeryDetailsController, 'Surgery Details', false),
                _buildDateField(_lastDentalVisitController, 'Last Dental Visit'),
                _buildDateField(_registeredAtController, 'Registration Date'),
              ]),

              SizedBox(height: 24),
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
                          : Text('Register Patient'),
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

  Widget _buildSection(String title, IconData icon, List<Widget> children) {
    return Container(
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
              Icon(icon, color: AppColors.primary, size: 20),
              SizedBox(width: 8),
              Text(
                title,
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          SizedBox(height: 12),
          ...children,
        ],
      ),
    );
  }

  Widget _buildTextField(TextEditingController controller, String label, bool required, [TextInputType? keyboardType]) {
    return Padding(
      padding: EdgeInsets.only(bottom: 12),
      child: TextFormField(
        controller: controller,
        keyboardType: keyboardType ?? TextInputType.text,
        decoration: InputDecoration(
          labelText: label,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          filled: true,
          fillColor: Colors.white,
        ),
        validator: required ? (value) {
          if (value == null || value.trim().isEmpty) {
            return 'This field is required';
          }
          return null;
        } : null,
      ),
    );
  }

  Widget _buildDateField(TextEditingController controller, String label) {
    return Padding(
      padding: EdgeInsets.only(bottom: 12),
      child: TextFormField(
        controller: controller,
        decoration: InputDecoration(
          labelText: label,
          hintText: 'YYYY-MM-DD',
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          filled: true,
          fillColor: Colors.white,
          suffixIcon: IconButton(
            icon: Icon(Icons.calendar_today),
            onPressed: () async {
              final date = await showDatePicker(
                context: context,
                initialDate: DateTime.now(),
                firstDate: DateTime(1900),
                lastDate: DateTime.now(),
              );
              if (date != null) {
                controller.text = date.toString().split(' ')[0];
              }
            },
          ),
        ),
        readOnly: true,
        onTap: () async {
          final date = await showDatePicker(
            context: context,
            initialDate: DateTime.now(),
            firstDate: DateTime(1900),
            lastDate: DateTime.now(),
          );
          if (date != null) {
            controller.text = date.toString().split(' ')[0];
          }
        },
      ),
    );
  }

  Widget _buildGenderSelector() {
    return Padding(
      padding: EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Gender *', style: TextStyle(fontWeight: FontWeight.w500)),
          SizedBox(height: 8),
          Row(
            children: [
              _buildGenderOption('M', 'Male'),
              SizedBox(width: 16),
              _buildGenderOption('F', 'Female'),
              SizedBox(width: 16),
              _buildGenderOption('O', 'Other'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildGenderOption(String value, String label) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Radio<String>(
          value: value,
          groupValue: _gender,
          onChanged: (val) => setState(() => _gender = val!),
          activeColor: AppColors.primary,
        ),
        Text(label),
      ],
    );
  }

  Widget _buildRadioSelector(String label, String value, Function(String) onChanged, List<String> options) {
    return Padding(
      padding: EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: TextStyle(fontWeight: FontWeight.w500)),
          SizedBox(height: 8),
          Row(
            children: options.map((opt) {
              final labels = {'no': 'No', 'yes': 'Yes'};
              return Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Radio<String>(
                    value: opt,
                    groupValue: value,
                    onChanged: (val) => onChanged(val!),
                    activeColor: AppColors.primary,
                  ),
                  Text(labels[opt] ?? opt),
                  SizedBox(width: 16),
                ],
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}

