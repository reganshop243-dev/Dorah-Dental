import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/colors.dart';

class DoctorsPage extends StatefulWidget {
  @override
  _DoctorsPageState createState() => _DoctorsPageState();
}

class _DoctorsPageState extends State<DoctorsPage> {
  List<dynamic> _doctors = [];
  bool _isLoading = true;
  String _errorMessage = '';
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _loadDoctors();
  }

  Future<void> _loadDoctors() async {
    setState(() => _isLoading = true);
    try {
      String url = 'doctors/';
      if (_searchQuery.isNotEmpty) {
        url += '?q=$_searchQuery';
      }

      print('👨‍⚕️ Loading doctors from: $url');
      final response = await ApiService.get(url);
      print('👨‍⚕️ Doctors response: $response');

      if (response is List) {
        setState(() {
          _doctors = response;
          _isLoading = false;
          _errorMessage = '';
        });
      } else if (response is Map && response.containsKey('results')) {
        setState(() {
          _doctors = response['results'] ?? [];
          _isLoading = false;
          _errorMessage = '';
        });
      } else if (response is Map && response.containsKey('data')) {
        setState(() {
          _doctors = response['data'] ?? [];
          _isLoading = false;
          _errorMessage = '';
        });
      } else {
        setState(() {
          _doctors = [];
          _isLoading = false;
          _errorMessage = 'Unexpected response format';
        });
      }
    } catch (e) {
      print('❌ Error loading doctors: $e');
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  // Helper to get doctor name
  String _getDoctorName(dynamic doctor) {
    // Try different field names
    if (doctor['display_name'] != null && doctor['display_name'].toString().isNotEmpty) {
      return doctor['display_name'];
    }
    if (doctor['name'] != null && doctor['name'].toString().isNotEmpty) {
      return doctor['name'];
    }
    if (doctor['first_name'] != null && doctor['first_name'].toString().isNotEmpty) {
      final lastName = doctor['last_name'] ?? '';
      return '${doctor['first_name']} $lastName'.trim();
    }
    return 'Unknown Doctor';
  }

  // Helper to get specialization
  String _getSpecialization(dynamic doctor) {
    final spec = doctor['specialization'] ?? '';
    if (spec.toString().isNotEmpty) {
      return spec;
    }
    return 'General';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Icon(Icons.person, color: Colors.white),
            SizedBox(width: 8),
            Text('Doctors'),
          ],
        ),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadDoctors,
          ),
        ],
      ),
      body: Column(
        children: [
          // Search Bar
          Container(
            padding: EdgeInsets.all(12),
            color: Colors.white,
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    decoration: InputDecoration(
                      hintText: 'Search doctors...',
                      prefixIcon: Icon(Icons.search, color: AppColors.muted),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12),
                    ),
                    onSubmitted: (value) {
                      setState(() => _searchQuery = value);
                      _loadDoctors();
                    },
                  ),
                ),
                SizedBox(width: 8),
                IconButton(
                  icon: Icon(Icons.clear, color: AppColors.muted),
                  onPressed: () {
                    setState(() {
                      _searchQuery = '';
                    });
                    _loadDoctors();
                  },
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
                  '${_doctors.length} doctors found',
                  style: TextStyle(color: AppColors.muted),
                ),
              ],
            ),
          ),
          // Doctor List
          Expanded(
            child: _isLoading
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(height: 16),
                        Text('Loading doctors...'),
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
                                onPressed: _loadDoctors,
                                child: Text('Retry'),
                              ),
                            ],
                          ),
                        ),
                      )
                    : _doctors.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.person, size: 64, color: AppColors.muted),
                                SizedBox(height: 16),
                                Text(
                                  'No Doctors Found',
                                  style: TextStyle(fontSize: 18),
                                ),
                                SizedBox(height: 8),
                                Text(
                                  'Add your first doctor',
                                  style: TextStyle(color: AppColors.muted),
                                ),
                                SizedBox(height: 16),
                                ElevatedButton(
                                  onPressed: () {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text('Add Doctor feature coming soon!')),
                                    );
                                  },
                                  child: Text('Add Doctor'),
                                ),
                              ],
                            ),
                          )
                        : ListView.builder(
                            padding: EdgeInsets.all(8),
                            itemCount: _doctors.length,
                            itemBuilder: (context, index) {
                              final doctor = _doctors[index];
                              final name = _getDoctorName(doctor);
                              final specialization = _getSpecialization(doctor);
                              final phone = doctor['phone'] ?? '';
                              final email = doctor['email'] ?? '';
                              final isActive = doctor['is_active'] ?? true;

                              return Card(
                                elevation: 1,
                                margin: EdgeInsets.only(bottom: 8),
                                child: ListTile(
                                  leading: CircleAvatar(
                                    backgroundColor: AppColors.primary,
                                    child: Text(
                                      name.isNotEmpty ? name[0].toUpperCase() : '?',
                                      style: TextStyle(color: Colors.white),
                                    ),
                                  ),
                                  title: Text(
                                    name,
                                    style: TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                  subtitle: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        specialization,
                                        style: TextStyle(
                                          color: AppColors.primary,
                                          fontWeight: FontWeight.w500,
                                          fontSize: 13,
                                        ),
                                      ),
                                      if (phone.isNotEmpty)
                                        Text(
                                          '📞 $phone',
                                          style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                                        ),
                                      if (email.isNotEmpty)
                                        Text(
                                          '✉️ $email',
                                          style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                                        ),
                                    ],
                                  ),
                                  trailing: Container(
                                    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: isActive 
                                          ? Colors.green.withOpacity(0.15) 
                                          : Colors.red.withOpacity(0.15),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Text(
                                      isActive ? 'Active' : 'Inactive',
                                      style: TextStyle(
                                        color: isActive ? Colors.green : Colors.red,
                                        fontSize: 10,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                  ),
                                  isThreeLine: true,
                                  onTap: () {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text('Viewing $name')),
                                    );
                                  },
                                ),
                              );
                            },
                          ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Add Doctor feature coming soon!')),
          );
        },
        backgroundColor: AppColors.primary,
        child: Icon(Icons.add),
      ),
    );
  }
}