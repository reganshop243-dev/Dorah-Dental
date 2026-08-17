import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/data_helper.dart';
import '../utils/colors.dart';

class InventoryPage extends StatefulWidget {
  @override
  _InventoryPageState createState() => _InventoryPageState();
}

class _InventoryPageState extends State<InventoryPage> {
  List<dynamic> _items = [];
  bool _isLoading = true;
  String _errorMessage = '';
  String _statusFilter = '';
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _loadItems();
  }

  Future<void> _loadItems() async {
    setState(() => _isLoading = true);
    try {
      // Build URL with filters
      String url = 'inventory/';
      List<String> params = [];
      
      // ✅ FIXED: Add actual search value
      if (_searchQuery.isNotEmpty) params.add('search=$_searchQuery');
      if (_statusFilter.isNotEmpty) params.add('status=$_statusFilter');
      
      if (params.isNotEmpty) url += '?' + params.join('&');

      print('📦 Loading inventory from: $url');
      final response = await ApiService.get(url);
      print('📦 Inventory response: $response');

      // Handle both List and Map responses
      if (response is List) {
        setState(() {
          _items = response;
          _isLoading = false;
          _errorMessage = '';
        });
      } else if (response is Map && response.containsKey('results')) {
        setState(() {
          _items = response['results'] ?? [];
          _isLoading = false;
          _errorMessage = '';
        });
      } else if (response is Map && response.containsKey('data')) {
        setState(() {
          _items = response['data'] ?? [];
          _isLoading = false;
          _errorMessage = '';
        });
      } else {
        setState(() {
          _items = [];
          _isLoading = false;
          _errorMessage = 'Unexpected response format';
        });
      }
    } catch (e) {
      print('❌ Error loading inventory: $e');
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
        title: Row(
          children: [
            Icon(Icons.inventory, color: Colors.white),
            SizedBox(width: 8),
            Text('Inventory'),
          ],
        ),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadItems,
          ),
        ],
      ),
      body: Column(
        children: [
          // Search and Filter
          Container(
            padding: EdgeInsets.all(12),
            color: Colors.white,
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    decoration: InputDecoration(
                      hintText: 'Search items...',
                      prefixIcon: Icon(Icons.search, color: AppColors.muted),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                      ),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12),
                    ),
                    onSubmitted: (value) {
                      setState(() => _searchQuery = value);
                      _loadItems();
                    },
                  ),
                ),
                SizedBox(width: 8),
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
                      DropdownMenuItem(value: 'available', child: Text('Available')),
                      DropdownMenuItem(value: 'low_stock', child: Text('Low Stock')),
                      DropdownMenuItem(value: 'out_of_stock', child: Text('Out of Stock')),
                    ],
                    onChanged: (value) {
                      setState(() => _statusFilter = value ?? '');
                      _loadItems();
                    },
                  ),
                ),
              ],
            ),
          ),
          
          // Stats Row
          Container(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: AppColors.cardBg,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildStatItem('Total', _items.length, Colors.blue),
                _buildStatItem(
                  'Low Stock',
                  _items.where((i) => i['status'] == 'low_stock' || (i['quantity'] ?? 0) <= (i['min_quantity'] ?? 5)).length,
                  Colors.orange,
                ),
                _buildStatItem(
                  'Out of Stock',
                  _items.where((i) => i['status'] == 'out_of_stock' || (i['quantity'] ?? 0) <= 0).length,
                  Colors.red,
                ),
              ],
            ),
          ),
          
          // Item List
          Expanded(
            child: _isLoading
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        CircularProgressIndicator(),
                        SizedBox(height: 16),
                        Text('Loading inventory...'),
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
                                onPressed: _loadItems,
                                child: Text('Retry'),
                              ),
                            ],
                          ),
                        ),
                      )
                    : _items.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.inventory, size: 64, color: AppColors.muted),
                                SizedBox(height: 16),
                                Text(
                                  'No Items Found',
                                  style: TextStyle(fontSize: 18),
                                ),
                                SizedBox(height: 8),
                                Text(
                                  'Add your first inventory item',
                                  style: TextStyle(color: AppColors.muted),
                                ),
                                SizedBox(height: 16),
                                ElevatedButton(
                                  onPressed: () {
                                    // Navigate to add inventory
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text('Add Inventory feature coming soon!')),
                                    );
                                  },
                                  child: Text('Add Item'),
                                ),
                              ],
                            ),
                          )
                        : ListView.builder(
                            padding: EdgeInsets.all(8),
                            itemCount: _items.length,
                            itemBuilder: (context, index) {
                              final item = _items[index];
                              final name = item['name'] ?? 'Unknown Item';
                              final category = item['category'] ?? item['category_name'] ?? 'Uncategorized';
                              final quantity = item['quantity'] ?? 0;
                              final minQuantity = item['min_quantity'] ?? 5;
                              final price = item['price'] ?? item['price_per_unit'] ?? 0.0;
                              
                              // Determine status
                              String status;
                              Color statusColor;
                              if (quantity <= 0) {
                                status = 'Out of Stock';
                                statusColor = Colors.red;
                              } else if (quantity <= minQuantity) {
                                status = 'Low Stock';
                                statusColor = Colors.orange;
                              } else {
                                status = 'Available';
                                statusColor = Colors.green;
                              }

                              return Card(
                                elevation: 1,
                                margin: EdgeInsets.only(bottom: 8),
                                child: ListTile(
                                  leading: Container(
                                    width: 40,
                                    height: 40,
                                    decoration: BoxDecoration(
                                      color: status == 'Low Stock' || status == 'Out of Stock'
                                          ? Colors.orange.withOpacity(0.15)
                                          : AppColors.primary.withOpacity(0.1),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Icon(
                                      status == 'Low Stock' || status == 'Out of Stock'
                                          ? Icons.warning
                                          : Icons.inventory,
                                      color: status == 'Low Stock' || status == 'Out of Stock'
                                          ? Colors.orange
                                          : AppColors.primary,
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
                                        category,
                                        style: TextStyle(fontSize: 12),
                                      ),
                                      Text(
                                        'Stock: $quantity units',
                                        style: TextStyle(
                                          color: status == 'Low Stock' || status == 'Out of Stock'
                                              ? Colors.orange
                                              : Colors.green,
                                          fontWeight: status == 'Low Stock' || status == 'Out of Stock'
                                              ? FontWeight.bold
                                              : FontWeight.normal,
                                          fontSize: 12,
                                        ),
                                      ),
                                      if (price > 0)
                                        Text(
                                          'Price: UGX ${price.toStringAsFixed(0)}',
                                          style: TextStyle(
                                            fontSize: 12,
                                            color: AppColors.muted,
                                          ),
                                        ),
                                    ],
                                  ),
                                  trailing: Container(
                                    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: statusColor.withOpacity(0.15),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Text(
                                      status,
                                      style: TextStyle(
                                        color: statusColor,
                                        fontSize: 10,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
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

  Widget _buildStatItem(String label, dynamic value, Color color) {
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
          style: TextStyle(fontSize: 11, color: AppColors.muted),
        ),
      ],
    );
  }
}