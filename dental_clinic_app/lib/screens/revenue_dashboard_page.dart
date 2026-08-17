import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/data_helper.dart';
import '../utils/colors.dart';

class RevenueDashboardPage extends StatefulWidget {
  @override
  _RevenueDashboardPageState createState() => _RevenueDashboardPageState();
}

class _RevenueDashboardPageState extends State<RevenueDashboardPage> {
  Map<String, dynamic> _data = {};
  bool _isLoading = true;
  String _errorMessage = '';
  String _period = 'this_month';
  
  final List<Map<String, dynamic>> _periods = [
    {'label': 'Today', 'value': 'today'},
    {'label': 'This Week', 'value': 'this_week'},
    {'label': 'This Month', 'value': 'this_month'},
    {'label': 'This Year', 'value': 'this_year'},
    {'label': 'All Time', 'value': 'all'},
  ];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      // ✅ FIXED: Correct endpoint with period parameter
      final response = await ApiService.get('revenue-dashboard/?period=$_period');
      print('💰 Revenue Dashboard Response: $response');
      
      if (response != null) {
        setState(() {
          _data = response;
          _isLoading = false;
        });
      } else {
        setState(() {
          _errorMessage = 'No data received';
          _isLoading = false;
        });
      }
    } catch (e) {
      print('❌ Error loading revenue data: $e');
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
        title: Text('Revenue Dashboard'),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadData,
          ),
        ],
      ),
      body: _isLoading
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Loading revenue data...'),
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
                          onPressed: _loadData,
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
                      // Period Selector
                      Container(
                        padding: EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Column(
                          children: [
                            Text(
                              'Select Period',
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                              ),
                            ),
                            SizedBox(height: 8),
                            Wrap(
                              spacing: 8,
                              runSpacing: 8,
                              children: _periods.map((p) {
                                final isSelected = _period == p['value'];
                                return FilterChip(
                                  label: Text(p['label']),
                                  selected: isSelected,
                                  onSelected: (selected) {
                                    setState(() {
                                      _period = p['value'];
                                      _loadData();
                                    });
                                  },
                                  selectedColor: AppColors.primary.withOpacity(0.2),
                                  backgroundColor: Colors.grey[50],
                                );
                              }).toList(),
                            ),
                          ],
                        ),
                      ),
                      
                      SizedBox(height: 16),
                      
                      // Revenue Stats
                      _buildStatRow(
                        'Period Revenue', 
                        _data['period_revenue'] ?? 0.0, 
                        Colors.blue,
                      ),
                      _buildStatRow(
                        'Total Revenue', 
                        _data['total_revenue'] ?? 0.0, 
                        Colors.green,
                      ),
                      _buildStatRow(
                        "Today's Revenue", 
                        _data['daily_revenue'] ?? 0.0, 
                        Colors.orange,
                      ),
                      _buildStatRow(
                        'Outstanding Balance', 
                        _data['total_outstanding'] ?? 0.0, 
                        Colors.red,
                      ),
                      
                      SizedBox(height: 16),
                      
                      // Invoice Status
                      Card(
                        child: Padding(
                          padding: EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Invoice Status',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              SizedBox(height: 12),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceAround,
                                children: [
                                  _buildStatusItem(
                                    'Total',
                                    _data['total_invoices'] ?? 0,
                                    Colors.blue,
                                  ),
                                  _buildStatusItem(
                                    'Paid',
                                    _data['paid_invoices'] ?? 0,
                                    Colors.green,
                                  ),
                                  _buildStatusItem(
                                    'Partially Paid',
                                    _data['partially_paid_invoices'] ?? 0,
                                    Colors.orange,
                                  ),
                                  _buildStatusItem(
                                    'Overdue',
                                    _data['overdue_invoices'] ?? 0,
                                    Colors.red,
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      
                      SizedBox(height: 16),
                      
                      // Monthly Chart (Simple)
                      if (_data['monthly_data'] != null && (_data['monthly_data'] as List).isNotEmpty)
                        Card(
                          child: Padding(
                            padding: EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Monthly Revenue',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                SizedBox(height: 12),
                                Container(
                                  height: 150,
                                  child: ListView.builder(
                                    scrollDirection: Axis.horizontal,
                                    itemCount: (_data['monthly_data'] as List).length,
                                    itemBuilder: (context, index) {
                                      final item = (_data['monthly_data'] as List)[index];
                                      final maxValue = _data['max_monthly_revenue'] ?? 1;
                                      final height = (item['revenue'] / maxValue * 100).clamp(0, 100);
                                      
                                      return Container(
                                        width: 50,
                                        margin: EdgeInsets.symmetric(horizontal: 4),
                                        child: Column(
                                          mainAxisAlignment: MainAxisAlignment.end,
                                          children: [
                                            Text(
                                              '${(item['revenue'] / 1000).toStringAsFixed(0)}k',
                                              style: TextStyle(
                                                fontSize: 8,
                                                color: AppColors.muted,
                                              ),
                                            ),
                                            Container(
                                              height: height,
                                              width: 30,
                                              decoration: BoxDecoration(
                                                color: AppColors.primary,
                                                borderRadius: BorderRadius.circular(4),
                                                gradient: LinearGradient(
                                                  begin: Alignment.bottomCenter,
                                                  end: Alignment.topCenter,
                                                  colors: [
                                                    AppColors.primary,
                                                    AppColors.primaryLight,
                                                  ],
                                                ),
                                              ),
                                            ),
                                            SizedBox(height: 4),
                                            Text(
                                              item['month']?.substring(0, 3) ?? '',
                                              style: TextStyle(
                                                fontSize: 10,
                                                color: AppColors.muted,
                                              ),
                                            ),
                                          ],
                                        ),
                                      );
                                    },
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      
                      // Recent Payments
                      if (_data['recent_payments'] != null && (_data['recent_payments'] as List).isNotEmpty)
                        Card(
                          child: Padding(
                            padding: EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Recent Payments',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                SizedBox(height: 8),
                                ...(_data['recent_payments'] as List).map((payment) {
                                  return ListTile(
                                    dense: true,
                                    leading: Icon(Icons.payment, color: Colors.green),
                                    title: Text('UGX ${payment['amount']?.toString() ?? '0'}'),
                                    subtitle: Text(payment['payment_date'] ?? ''),
                                    trailing: Chip(
                                      label: Text('Completed'),
                                      backgroundColor: Colors.green[100],
                                    ),
                                  );
                                }).toList(),
                              ],
                            ),
                          ),
                        ),
                      
                      // Top Patients
                      if (_data['top_patients'] != null && (_data['top_patients'] as List).isNotEmpty)
                        Card(
                          child: Padding(
                            padding: EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Top Patients',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                SizedBox(height: 8),
                                ...(_data['top_patients'] as List).map((patient) {
                                  final name = '${patient['patient__first_name'] ?? ''} ${patient['patient__last_name'] ?? ''}';
                                  return ListTile(
                                    dense: true,
                                    leading: CircleAvatar(
                                      child: Text(name.isNotEmpty ? name[0].toUpperCase() : '?'),
                                      backgroundColor: AppColors.primary,
                                      foregroundColor: Colors.white,
                                    ),
                                    title: Text(name.isNotEmpty ? name : 'Unknown'),
                                    trailing: Text(
                                      'UGX ${patient['total_spent']?.toString() ?? '0'}',
                                      style: TextStyle(
                                        fontWeight: FontWeight.bold,
                                        color: Colors.green,
                                      ),
                                    ),
                                  );
                                }).toList(),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
    );
  }

  Widget _buildStatRow(String label, dynamic value, Color color) {
    return Card(
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              label,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
            Text(
              'UGX ${value.toStringAsFixed(0)}',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatusItem(String label, dynamic value, Color color) {
    return Column(
      children: [
        Text(
          value.toString(),
          style: TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            color: AppColors.muted,
          ),
        ),
      ],
    );
  }
}