import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../api/api_service.dart';
import '../utils/colors.dart';
import 'patient_detail_screen.dart';
import 'patient_add_screen.dart';

class PatientsPage extends StatefulWidget {
  @override
  _PatientsPageState createState() => _PatientsPageState();
}

class _PatientsPageState extends State<PatientsPage> {
  List<dynamic> _patients = [];
  bool _isLoading = true;
  String _errorMessage = '';
  String _searchQuery = '';
  String _balanceFilter = '';
  String _sortFilter = '-registered_at';

  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadPatients();
  }

  Future<void> _loadPatients() async {
    setState(() => _isLoading = true);
    try {
      String url = 'patients/';
      List<String> params = [];
      if (_searchQuery.isNotEmpty) params.add('q=$_searchQuery');
      if (_balanceFilter.isNotEmpty) params.add('balance=$_balanceFilter');
      if (_sortFilter.isNotEmpty) params.add('sort=$_sortFilter');
      if (params.isNotEmpty) url += '?' + params.join('&');

      print('👤 Loading patients from: $url');
      final response = await ApiService.get(url);
      print('👤 Patients response: $response');

      if (response is List) {
        setState(() {
          _patients = response;
          _isLoading = false;
          _errorMessage = '';
        });
      } else if (response is Map && response.containsKey('results')) {
        setState(() {
          _patients = response['results'] ?? [];
          _isLoading = false;
          _errorMessage = '';
        });
      } else if (response is Map && response.containsKey('data')) {
        setState(() {
          _patients = response['data'] ?? [];
          _isLoading = false;
          _errorMessage = '';
        });
      } else {
        setState(() {
          _patients = [];
          _isLoading = false;
          _errorMessage = 'Unexpected response format';
        });
      }
    } catch (e) {
      print('❌ Error loading patients: $e');
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  // Helper function to get balance from patient
  double _getPatientBalance(dynamic patient) {
    // Try different possible field names
    dynamic balanceValue = patient['balance'] ?? 
                          patient['outstanding'] ?? 
                          patient['due'] ?? 
                          patient['balance_due'] ?? 
                          0;
    
    if (balanceValue is num) {
      return balanceValue.toDouble();
    } else if (balanceValue is String) {
      return double.tryParse(balanceValue) ?? 0.0;
    }
    return 0.0;
  }

  void _navigateToPatientDetail(int id) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => PatientDetailScreen(patientId: id)),
    ).then((_) => _loadPatients());
  }

  void _navigateToAddPatient() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => PatientAddScreen()),
    ).then((_) => _loadPatients());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Icon(Icons.people, color: Colors.white),
            SizedBox(width: 8),
            Text('Patients'),
          ],
        ),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadPatients,
          ),
        ],
      ),
      body: Column(
        children: [
          // Search and Filters
          Container(
            padding: EdgeInsets.all(12),
            color: Colors.white,
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _searchController,
                        decoration: InputDecoration(
                          hintText: 'Search patients...',
                          prefixIcon: Icon(Icons.search, color: AppColors.muted),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          contentPadding: EdgeInsets.symmetric(horizontal: 12),
                        ),
                        onSubmitted: (value) {
                          setState(() => _searchQuery = value);
                          _loadPatients();
                        },
                      ),
                    ),
                    SizedBox(width: 8),
                    IconButton(
                      icon: Icon(Icons.clear, color: AppColors.muted),
                      onPressed: () {
                        _searchController.clear();
                        setState(() => _searchQuery = '');
                        _loadPatients();
                      },
                    ),
                  ],
                ),
                SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        value: _balanceFilter.isEmpty ? null : _balanceFilter,
                        decoration: InputDecoration(
                          hintText: 'Balance',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          contentPadding: EdgeInsets.symmetric(horizontal: 12),
                        ),
                        items: [
                          DropdownMenuItem(value: '', child: Text('All Patients')),
                          DropdownMenuItem(value: 'has_balance', child: Text('With Balance')),
                          DropdownMenuItem(value: 'no_balance', child: Text('Without Balance')),
                        ],
                        onChanged: (value) {
                          setState(() => _balanceFilter = value ?? '');
                          _loadPatients();
                        },
                      ),
                    ),
                    SizedBox(width: 8),
                    Expanded(
                      child: DropdownButtonFormField<String>(
                        value: _sortFilter,
                        decoration: InputDecoration(
                          hintText: 'Sort',
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          contentPadding: EdgeInsets.symmetric(horizontal: 12),
                        ),
                        items: [
                          DropdownMenuItem(value: '-registered_at', child: Text('Newest First')),
                          DropdownMenuItem(value: 'registered_at', child: Text('Oldest First')),
                          DropdownMenuItem(value: 'first_name', child: Text('Name A-Z')),
                          DropdownMenuItem(value: '-first_name', child: Text('Name Z-A')),
                        ],
                        onChanged: (value) {
                          setState(() => _sortFilter = value ?? '-registered_at');
                          _loadPatients();
                        },
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          // Results count
          Container(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: AppColors.cardBg,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  '${_patients.length} patients found',
                  style: TextStyle(color: AppColors.muted),
                ),
                TextButton(
                  onPressed: _patients.isNotEmpty ? () => _exportCSV() : null,
                  child: Row(
                    children: [
                      Icon(Icons.download, size: 16),
                      SizedBox(width: 4),
                      Text('Export'),
                    ],
                  ),
                ),
              ],
            ),
          ),
          // Patient List
          Expanded(
            child: _isLoading
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(height: 16),
                        Text('Loading patients...'),
                      ],
                    ),
                  )
                : _errorMessage.isNotEmpty
                    ? Center(
                        child: Padding(
                          padding: EdgeInsets.all(32),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.error_outline, size: 64, color: Colors.red),
                              SizedBox(height: 16),
                              Text(
                                _errorMessage,
                                textAlign: TextAlign.center,
                              ),
                              SizedBox(height: 16),
                              ElevatedButton(
                                onPressed: _loadPatients,
                                child: Text('Retry'),
                              ),
                            ],
                          ),
                        ),
                      )
                    : _patients.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.people, size: 64, color: AppColors.muted),
                                SizedBox(height: 16),
                                Text(
                                  'No Patients Found',
                                  style: TextStyle(fontSize: 18),
                                ),
                                SizedBox(height: 8),
                                Text(
                                  'Add your first patient',
                                  style: TextStyle(color: AppColors.muted),
                                ),
                                SizedBox(height: 16),
                                ElevatedButton(
                                  onPressed: _navigateToAddPatient,
                                  child: Text('Add Patient'),
                                ),
                              ],
                            ),
                          )
                        : ListView.builder(
                            padding: EdgeInsets.all(8),
                            itemCount: _patients.length,
                            itemBuilder: (context, index) {
                              final patient = _patients[index];
                              final firstName = patient['first_name'] ?? '';
                              final lastName = patient['last_name'] ?? '';
                              final fullName = '$firstName $lastName'.trim();
                              final phone = patient['phone'] ?? '';
                              final email = patient['email'] ?? '';
                              final balance = _getPatientBalance(patient);

                              return Card(
                                elevation: 1,
                                margin: EdgeInsets.only(bottom: 8),
                                child: ListTile(
                                  leading: CircleAvatar(
                                    backgroundColor: AppColors.primary,
                                    child: Text(
                                      fullName.isNotEmpty ? fullName[0].toUpperCase() : '?',
                                      style: TextStyle(color: Colors.white),
                                    ),
                                  ),
                                  title: Text(
                                    fullName.isNotEmpty ? fullName : 'Unknown Patient',
                                    style: TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                  subtitle: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      if (phone.isNotEmpty)
                                        Text(
                                          phone,
                                          style: TextStyle(fontSize: 12),
                                        ),
                                      if (email.isNotEmpty)
                                        Text(
                                          email,
                                          style: TextStyle(fontSize: 12),
                                        ),
                                      if (phone.isEmpty && email.isEmpty)
                                        Text(
                                          'No contact info',
                                          style: TextStyle(fontSize: 12, color: AppColors.muted),
                                        ),
                                    ],
                                  ),
                                  trailing: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      if (balance > 0)
                                        Container(
                                          padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                          decoration: BoxDecoration(
                                            color: Colors.red.withOpacity(0.15),
                                            borderRadius: BorderRadius.circular(12),
                                          ),
                                          child: Text(
                                            'UGX ${balance.toStringAsFixed(0)}',
                                            style: TextStyle(
                                              color: Colors.red,
                                              fontSize: 12,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                      if (balance == 0)
                                        Container(
                                          padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                          decoration: BoxDecoration(
                                            color: Colors.green.withOpacity(0.15),
                                            borderRadius: BorderRadius.circular(12),
                                          ),
                                          child: Text(
                                            'Paid',
                                            style: TextStyle(
                                              color: Colors.green,
                                              fontSize: 10,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                      SizedBox(width: 4),
                                      IconButton(
                                        icon: Icon(Icons.chevron_right),
                                        onPressed: () => _navigateToPatientDetail(patient['id']),
                                      ),
                                    ],
                                  ),
                                  onTap: () => _navigateToPatientDetail(patient['id']),
                                ),
                              );
                            },
                          ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _navigateToAddPatient,
        backgroundColor: AppColors.primary,
        child: Icon(Icons.add),
      ),
    );
  }

  void _exportCSV() {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Exporting ${_patients.length} patients...')),
    );
  }
}