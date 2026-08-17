import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/colors.dart';

class BalanceSheetPage extends StatefulWidget {
  @override
  _BalanceSheetPageState createState() => _BalanceSheetPageState();
}

class _BalanceSheetPageState extends State<BalanceSheetPage> {
  Map<String, dynamic> _data = {};
  bool _isLoading = true;
  String _errorMessage = '';
  DateTime? _startDate;
  DateTime? _endDate;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    try {
      String url = 'balance-sheet/';
      List<String> params = [];
      
      if (_startDate != null) {
        params.add('start_date=${_startDate!.toIso8601String().split('T')[0]}');
      }
      if (_endDate != null) {
        params.add('end_date=${_endDate!.toIso8601String().split('T')[0]}');
      }
      
      if (params.isNotEmpty) url += '?' + params.join('&');

      print('📋 Loading balance sheet from: $url');
      final response = await ApiService.get(url);
      print('📋 Balance sheet response: $response');
      
      setState(() {
        _data = response is Map<String, dynamic> ? response : {};
        _isLoading = false;
        _errorMessage = '';
      });
    } catch (e) {
      print('❌ Error loading balance sheet: $e');
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
        title: Text('Balance Sheet'),
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
                  Text('Loading balance sheet...'),
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
                      // Date Filter
                      Card(
                        child: Padding(
                          padding: EdgeInsets.all(16),
                          child: Column(
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: GestureDetector(
                                      onTap: () => _selectDate(context, true),
                                      child: Container(
                                        padding: EdgeInsets.all(12),
                                        decoration: BoxDecoration(
                                          border: Border.all(color: AppColors.border),
                                          borderRadius: BorderRadius.circular(8),
                                        ),
                                        child: Row(
                                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                          children: [
                                            Text(
                                              _startDate != null
                                                  ? '${_startDate!.year}-${_startDate!.month.toString().padLeft(2, '0')}-${_startDate!.day.toString().padLeft(2, '0')}'
                                                  : 'Start Date',
                                              style: TextStyle(
                                                color: _startDate != null
                                                    ? Colors.black
                                                    : AppColors.muted,
                                              ),
                                            ),
                                            Icon(Icons.calendar_today, size: 16),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                  SizedBox(width: 8),
                                  Expanded(
                                    child: GestureDetector(
                                      onTap: () => _selectDate(context, false),
                                      child: Container(
                                        padding: EdgeInsets.all(12),
                                        decoration: BoxDecoration(
                                          border: Border.all(color: AppColors.border),
                                          borderRadius: BorderRadius.circular(8),
                                        ),
                                        child: Row(
                                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                          children: [
                                            Text(
                                              _endDate != null
                                                  ? '${_endDate!.year}-${_endDate!.month.toString().padLeft(2, '0')}-${_endDate!.day.toString().padLeft(2, '0')}'
                                                  : 'End Date',
                                              style: TextStyle(
                                                color: _endDate != null
                                                    ? Colors.black
                                                    : AppColors.muted,
                                              ),
                                            ),
                                            Icon(Icons.calendar_today, size: 16),
                                          ],
                                        ),
                                      ),
                                    ),
                                  ),
                                  SizedBox(width: 8),
                                  ElevatedButton(
                                    onPressed: _loadData,
                                    child: Text('Apply'),
                                  ),
                                ],
                              ),
                              SizedBox(height: 8),
                              Row(
                                children: [
                                  TextButton(
                                    onPressed: () {
                                      setState(() {
                                        _startDate = null;
                                        _endDate = null;
                                      });
                                      _loadData();
                                    },
                                    child: Text('Clear Filters'),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      
                      SizedBox(height: 16),
                      
                      // Summary Cards
                      _buildSummaryCard(
                        'Total Revenue',
                        _data['total_revenue'] ?? 0.0,
                        Colors.green,
                      ),
                      _buildSummaryCard(
                        'Total Expenses',
                        _data['total_expenses'] ?? 0.0,
                        Colors.red,
                      ),
                      _buildSummaryCard(
                        'Net Profit',
                        _data['net_profit'] ?? 0.0,
                        (_data['net_profit'] ?? 0.0) >= 0 ? Colors.blue : Colors.red,
                      ),
                      _buildSummaryCard(
                        'Outstanding Balance',
                        _data['pending_amount'] ?? 0.0,
                        Colors.orange,
                      ),
                      
                      SizedBox(height: 16),
                      
                      // Invoice Summary
                      Card(
                        child: Padding(
                          padding: EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Invoice Summary',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              SizedBox(height: 12),
                              Row(
                                mainAxisAlignment: MainAxisAlignment.spaceAround,
                                children: [
                                  _buildInvoiceStatus(
                                    'Total',
                                    _data['total_invoices'] ?? 0,
                                    Colors.blue,
                                  ),
                                  _buildInvoiceStatus(
                                    'Paid',
                                    _data['paid_invoices'] ?? 0,
                                    Colors.green,
                                  ),
                                  _buildInvoiceStatus(
                                    'Pending',
                                    _data['pending_invoices'] ?? 0,
                                    Colors.orange,
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                      
                      SizedBox(height: 16),
                      
                      // Revenue by Method
                      if (_data['revenue_by_method'] != null && (_data['revenue_by_method'] as List).isNotEmpty)
                        Card(
                          child: Padding(
                            padding: EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Revenue by Payment Method',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                SizedBox(height: 12),
                                ...(_data['revenue_by_method'] as List).map((item) => Padding(
                                  padding: EdgeInsets.symmetric(vertical: 4),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(item['payment_method'] ?? 'Unknown'),
                                      Text(
                                        'UGX ${(item['total'] ?? 0.0).toStringAsFixed(0)}',
                                        style: TextStyle(
                                          fontWeight: FontWeight.bold,
                                          color: Colors.green,
                                        ),
                                      ),
                                    ],
                                  ),
                                )).toList(),
                              ],
                            ),
                          ),
                        ),
                      
                      // Expenses by Category
                      if (_data['expenses_by_category'] != null && (_data['expenses_by_category'] as List).isNotEmpty)
                        Card(
                          child: Padding(
                            padding: EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'Expenses by Category',
                                  style: TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                SizedBox(height: 12),
                                ...(_data['expenses_by_category'] as List).map((item) => Padding(
                                  padding: EdgeInsets.symmetric(vertical: 4),
                                  child: Row(
                                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                    children: [
                                      Text(item['category'] ?? 'Unknown'),
                                      Text(
                                        'UGX ${(item['total'] ?? 0.0).toStringAsFixed(0)}',
                                        style: TextStyle(
                                          fontWeight: FontWeight.bold,
                                          color: Colors.red,
                                        ),
                                      ),
                                    ],
                                  ),
                                )).toList(),
                              ],
                            ),
                          ),
                        ),
                      
                      // Period Info
                      Card(
                        child: Padding(
                          padding: EdgeInsets.all(12),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.info_outline, size: 16, color: AppColors.muted),
                              SizedBox(width: 8),
                              Text(
                                'Period: ${_data['start_date'] ?? 'N/A'} to ${_data['end_date'] ?? 'N/A'}',
                                style: TextStyle(
                                  color: AppColors.muted,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
    );
  }

  Widget _buildSummaryCard(String label, dynamic value, Color color) {
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
              'UGX ${(value ?? 0.0).toStringAsFixed(0)}',
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

  Widget _buildInvoiceStatus(String label, dynamic value, Color color) {
    return Column(
      children: [
        Text(
          value.toString(),
          style: TextStyle(
            fontSize: 18,
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

  Future<void> _selectDate(BuildContext context, bool isStart) async {
    final date = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2020, 1, 1),
      lastDate: DateTime.now(),
    );
    if (date != null) {
      setState(() {
        if (isStart) {
          _startDate = date;
        } else {
          _endDate = date;
        }
      });
      _loadData();
    }
  }
}