import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/colors.dart';

class InventoryPage extends StatefulWidget {
  @override
  _InventoryPageState createState() => _InventoryPageState();
}

class _InventoryPageState extends State<InventoryPage> {
  List<dynamic> _items = [];
  bool _isLoading = true;
  String _errorMessage = '';
  String _categoryFilter = '';
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
      String url = 'inventory/';
      List<String> params = [];
      if (_searchQuery.isNotEmpty) params.add('search=');
      if (_categoryFilter.isNotEmpty) params.add('category=');
      if (_statusFilter.isNotEmpty) params.add('status=');
      if (params.isNotEmpty) url += '?' + params.join('&');

      final response = await ApiService.get(url);
      
      if (response is List) {
        _items = response;
      } else if (response is Map && response.containsKey('results')) {
        _items = response['results'] ?? [];
      } else if (response is Map && response.containsKey('data')) {
        _items = response['data'] ?? [];
      } else {
        _items = [];
      }
      _isLoading = false;
    } catch (e) {
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
          // Search
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
          // Stats
          Container(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: AppColors.cardBg,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildStatItem('Total', _items.length, Colors.blue),
                _buildStatItem(
                  'Low Stock',
                  _items.where((i) => i['status'] == 'low_stock').length,
                  Colors.orange,
                ),
                _buildStatItem(
                  'Out of Stock',
                  _items.where((i) => i['status'] == 'out_of_stock').length,
                  Colors.red,
                ),
              ],
            ),
          ),
          // Item List
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
                                Text('No Items', style: TextStyle(fontSize: 18)),
                                SizedBox(height: 8),
                                Text('Add your first inventory item', style: TextStyle(color: AppColors.muted)),
                              ],
                            ),
                          )
                        : ListView.builder(
                            padding: EdgeInsets.all(8),
                            itemCount: _items.length,
                            itemBuilder: (context, index) {
                              final item = _items[index];
                              final quantity = item['quantity'] ?? 0;
                              final status = item['status'] ?? 'available';
                              final isLowStock = status == 'low_stock' || quantity <= (item['min_quantity'] ?? 5);

                              return Card(
                                elevation: 1,
                                margin: EdgeInsets.only(bottom: 8),
                                child: ListTile(
                                  leading: Container(
                                    width: 40,
                                    height: 40,
                                    decoration: BoxDecoration(
                                      color: isLowStock
                                          ? Colors.orange.withOpacity(0.15)
                                          : AppColors.primary.withOpacity(0.1),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Icon(
                                      isLowStock ? Icons.warning : Icons.inventory,
                                      color: isLowStock ? Colors.orange : AppColors.primary,
                                    ),
                                  ),
                                  title: Text(
                                    item['name'] ?? 'Unknown',
                                    style: TextStyle(fontWeight: FontWeight.bold),
                                  ),
                                  subtitle: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(item['category_name'] ?? 'Uncategorized'),
                                      Text(
                                        'Stock:  ',
                                        style: TextStyle(
                                          color: isLowStock ? Colors.orange : Colors.green,
                                          fontWeight: isLowStock ? FontWeight.bold : FontWeight.normal,
                                        ),
                                      ),
                                    ],
                                  ),
                                  trailing: Container(
                                    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: status == 'available'
                                          ? Colors.green.withOpacity(0.15)
                                          : status == 'low_stock'
                                              ? Colors.orange.withOpacity(0.15)
                                              : Colors.red.withOpacity(0.15),
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                    child: Text(
                                      status == 'available'
                                          ? 'Available'
                                          : status == 'low_stock'
                                              ? 'Low Stock'
                                              : 'Out of Stock',
                                      style: TextStyle(
                                        color: status == 'available'
                                            ? Colors.green
                                            : status == 'low_stock'
                                                ? Colors.orange
                                                : Colors.red,
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
