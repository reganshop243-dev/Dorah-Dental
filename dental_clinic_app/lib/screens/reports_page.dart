import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/data_helper.dart';
import '../utils/colors.dart';

class ReportsPage extends StatefulWidget {
  @override
  _ReportsPageState createState() => _ReportsPageState();
}

class _ReportsPageState extends State<ReportsPage> {
  Map<String, dynamic> _agingData = {};
  Map<String, dynamic> _patientVisits = {};
  Map<String, dynamic> _doctorPerformance = {};
  bool _isLoading = true;
  String _errorMessage = '';

  final List<String> _tabs = ['Aging', 'Patient Visits', 'Doctor Performance'];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      final agingResponse = await ApiService.get('reports/aging/');
      final visitsResponse = await ApiService.get('reports/patient-visits/');
      final performanceResponse = await ApiService.get('reports/doctor-performance/');
      
      setState(() {
        _agingData = DataHelper.safeGetMap(agingResponse);
        _patientVisits = DataHelper.safeGetMap(visitsResponse);
        _doctorPerformance = DataHelper.safeGetMap(performanceResponse);
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
    return DefaultTabController(
      length: _tabs.length,
      child: Scaffold(
        appBar: AppBar(
          title: Text('Reports'),
          backgroundColor: AppColors.primary,
          foregroundColor: Colors.white,
          bottom: TabBar(
            isScrollable: true,
            labelColor: Colors.white,
            unselectedLabelColor: Colors.white70,
            indicatorColor: Colors.white,
            tabs: _tabs.map((tab) => Tab(text: tab)).toList(),
          ),
          actions: [
            IconButton(
              icon: Icon(Icons.refresh),
              onPressed: _loadData,
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
                            onPressed: _loadData,
                            child: Text('Retry'),
                          ),
                        ],
                      ),
                    ),
                  )
                : TabBarView(
                    children: [
                      _buildAgingReport(),
                      _buildPatientVisits(),
                      _buildDoctorPerformance(),
                    ],
                  ),
      ),
    );
  }

  Widget _buildAgingReport() {
    final data = _agingData['aging_data'] ?? {};
    final invoices = data['invoices'] ?? [];
    return SingleChildScrollView(
      padding: EdgeInsets.all(16),
      child: Column(
        children: [
          GridView.count(
            shrinkWrap: true,
            physics: NeverScrollableScrollPhysics(),
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            children: [
              _buildAgingCard('Over 90 Days', data['over_90'] ?? 0, Colors.red),
              _buildAgingCard('61-90 Days', data['sixty_ninety'] ?? 0, Colors.orange),
              _buildAgingCard('31-60 Days', data['thirty_sixty'] ?? 0, Colors.blue),
              _buildAgingCard('0-30 Days', data['zero_thirty'] ?? 0, Colors.green),
            ],
          ),
          SizedBox(height: 16),
          if (invoices.isNotEmpty)
            Card(
              child: Padding(
                padding: EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Outstanding Invoices', style: TextStyle(fontWeight: FontWeight.bold)),
                    SizedBox(height: 8),
                    ...invoices.map((invoice) => ListTile(
                      dense: true,
                      title: Text(invoice['patient_name'] ?? 'Unknown'),
                      subtitle: Text(' -  days'),
                      trailing: Text(
                        'UGX ',
                        style: TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
                      ),
                    )),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildPatientVisits() {
    final patients = _patientVisits['patients'] ?? [];
    return SingleChildScrollView(
      padding: EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(child: _buildVisitStat('Total Patients', _patientVisits['total_patients'] ?? 0, Colors.blue)),
              SizedBox(width: 8),
              Expanded(child: _buildVisitStat('Total Visits', _patientVisits['total_visits'] ?? 0, Colors.green)),
            ],
          ),
          SizedBox(height: 8),
          Row(
            children: [
              Expanded(child: _buildVisitStat('New Patients', _patientVisits['new_patients'] ?? 0, Colors.orange)),
              SizedBox(width: 8),
              Expanded(child: _buildVisitStat('Returning', _patientVisits['returning_patients'] ?? 0, Colors.purple)),
            ],
          ),
          SizedBox(height: 16),
          if (patients.isNotEmpty)
            Card(
              child: Padding(
                padding: EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Patient Visits', style: TextStyle(fontWeight: FontWeight.bold)),
                    SizedBox(height: 8),
                    ...patients.map((patient) => ListTile(
                      dense: true,
                      title: Text(patient['full_name'] ?? 'Unknown'),
                      subtitle: Text(' visits'),
                      trailing: Text('UGX ', style: TextStyle(fontWeight: FontWeight.bold)),
                    )),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildDoctorPerformance() {
    final doctors = _doctorPerformance['doctors'] ?? [];
    return SingleChildScrollView(
      padding: EdgeInsets.all(16),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(child: _buildPerformanceStat('Total Revenue', _doctorPerformance['total_revenue'] ?? 0, Colors.green)),
              SizedBox(width: 8),
              Expanded(child: _buildPerformanceStat('Appointments', _doctorPerformance['total_appointments'] ?? 0, Colors.blue)),
            ],
          ),
          SizedBox(height: 16),
          if (doctors.isNotEmpty)
            ...doctors.map((doctor) => Card(
              margin: EdgeInsets.only(bottom: 8),
              child: Padding(
                padding: EdgeInsets.all(12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(doctor['name'] ?? 'Unknown', style: TextStyle(fontWeight: FontWeight.bold)),
                        Text(doctor['specialization'] ?? 'General', style: TextStyle(color: AppColors.muted)),
                      ],
                    ),
                    SizedBox(height: 8),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildMetric('Revenue', 'UGX '),
                        _buildMetric('Patients', ''),
                        _buildMetric('Appointments', ''),
                      ],
                    ),
                  ],
                ),
              ),
            )),
        ],
      ),
    );
  }

  Widget _buildAgingCard(String label, dynamic value, Color color) {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(12),
        child: Column(
          children: [
            Text(
              'UGX ',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color),
            ),
            Text(label, style: TextStyle(fontSize: 11, color: AppColors.muted)),
          ],
        ),
      ),
    );
  }

  Widget _buildVisitStat(String label, dynamic value, Color color) {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(12),
        child: Column(
          children: [
            Text(
              value.toString(),
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: color),
            ),
            Text(label, style: TextStyle(fontSize: 11, color: AppColors.muted)),
          ],
        ),
      ),
    );
  }

  Widget _buildPerformanceStat(String label, dynamic value, Color color) {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(12),
        child: Column(
          children: [
            Text(
              value.toString(),
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: color),
            ),
            Text(label, style: TextStyle(fontSize: 11, color: AppColors.muted)),
          ],
        ),
      ),
    );
  }

  Widget _buildMetric(String label, String value) {
    return Column(
      children: [
        Text(value, style: TextStyle(fontWeight: FontWeight.bold)),
        Text(label, style: TextStyle(fontSize: 10, color: AppColors.muted)),
      ],
    );
  }
}
