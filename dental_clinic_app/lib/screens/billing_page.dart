import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/data_helper.dart';
import '../utils/colors.dart';

class BillingPage extends StatefulWidget {
  @override
  _BillingPageState createState() => _BillingPageState();
}

class _BillingPageState extends State<BillingPage> {
  List<dynamic> _invoices = [];
  bool _isLoading = true;
  String _errorMessage = '';
  String _statusFilter = '';

  @override
  void initState() {
    super.initState();
    _loadInvoices();
  }

  Future<void> _loadInvoices() async {
    setState(() => _isLoading = true);
    try {
      String url = 'invoices/';
      if (_statusFilter.isNotEmpty) url += '?status=';

      final response = await ApiService.get(url);
      _invoices = DataHelper.safeGetList(response);
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
      case 'paid': return Colors.green;
      case 'partially_paid': return Colors.orange;
      case 'overdue': return Colors.red;
      case 'draft': return Colors.grey;
      case 'sent': return Colors.blue;
      default: return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Icon(Icons.receipt, color: Colors.white),
            SizedBox(width: 8),
            Text('Billing'),
          ],
        ),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadInvoices,
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
                      DropdownMenuItem(value: 'paid', child: Text('Paid')),
                      DropdownMenuItem(value: 'partially_paid', child: Text('Partially Paid')),
                      DropdownMenuItem(value: 'overdue', child: Text('Overdue')),
                      DropdownMenuItem(value: 'draft', child: Text('Draft')),
                    ],
                    onChanged: (value) {
                      setState(() => _statusFilter = value ?? '');
                      _loadInvoices();
                    },
                  ),
                ),
                SizedBox(width: 8),
                ElevatedButton(
                  onPressed: _loadInvoices,
                  child: Text('Apply'),
                ),
              ],
            ),
          ),
          Container(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: AppColors.cardBg,
            child: Text(
              ' invoices',
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
                                onPressed: _loadInvoices,
                                child: Text('Retry'),
                              ),
                            ],
                          ),
                        ),
                      )
                    : _invoices.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.receipt, size: 64, color: AppColors.muted),
                                SizedBox(height: 16),
                                Text('No Invoices', style: TextStyle(fontSize: 18)),
                                SizedBox(height: 8),
                                Text('Create your first invoice', style: TextStyle(color: AppColors.muted)),
                              ],
                            ),
                          )
                        : ListView.builder(
                            padding: EdgeInsets.all(8),
                            itemCount: _invoices.length,
                            itemBuilder: (context, index) {
                              final invoice = _invoices[index];
                              final balance = (invoice['balance_due'] ?? 0).toDouble();

                              return Card(
                                elevation: 1,
                                margin: EdgeInsets.only(bottom: 8),
                                child: ListTile(
                                  leading: Container(
                                    width: 40,
                                    height: 40,
                                    decoration: BoxDecoration(
                                      color: _getStatusColor(invoice['status']).withOpacity(0.15),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Icon(Icons.receipt, color: _getStatusColor(invoice['status'])),
                                  ),
                                  title: Text(
                                    invoice['invoice_number'] ?? 'N/A',
                                    style: TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                  subtitle: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(invoice['patient_name'] ?? 'Unknown Patient'),
                                      Text(invoice['issue_date'] ?? '', style: TextStyle(fontSize: 12)),
                                    ],
                                  ),
                                  trailing: Column(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    crossAxisAlignment: CrossAxisAlignment.end,
                                    children: [
                                      Text(
                                        'UGX ',
                                        style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.primary),
                                      ),
                                      if (balance > 0)
                                        Text(
                                          'Balance: UGX ',
                                          style: TextStyle(color: Colors.red, fontSize: 12, fontWeight: FontWeight.bold),
                                        ),
                                      Container(
                                        margin: EdgeInsets.only(top: 4),
                                        padding: EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: _getStatusColor(invoice['status']).withOpacity(0.15),
                                          borderRadius: BorderRadius.circular(8),
                                        ),
                                        child: Text(
                                          invoice['status'] ?? 'Unknown',
                                          style: TextStyle(
                                            color: _getStatusColor(invoice['status']),
                                            fontSize: 10,
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                  isThreeLine: true,
                                ),
                              );
                            },
                          ),
          ),
        ],
      ),
    );
  }
}
