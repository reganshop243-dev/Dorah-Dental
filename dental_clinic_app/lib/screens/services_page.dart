import 'package:flutter/material.dart';
import '../api/api_service.dart';
import '../utils/colors.dart';

class ServicesPage extends StatefulWidget {
  @override
  _ServicesPageState createState() => _ServicesPageState();
}

class _ServicesPageState extends State<ServicesPage> {
  List<dynamic> _services = [];
  bool _isLoading = true;
  String _errorMessage = '';
  bool _showInactive = false;

  @override
  void initState() {
    super.initState();
    _loadServices();
  }

  Future<void> _loadServices() async {
    setState(() => _isLoading = true);
    try {
      final response = await ApiService.get('services/');
      
      // Handle different response formats
      if (response is List) {
        _services = response;
      } else if (response is Map && response.containsKey('results')) {
        _services = response['results'] ?? [];
      } else if (response is Map && response.containsKey('data')) {
        _services = response['data'] ?? [];
      } else {
        _services = [];
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
    final filteredServices = _showInactive
        ? _services
        : _services.where((s) => s['is_active'] != false).toList();

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Icon(Icons.medical_services, color: Colors.white),
            SizedBox(width: 8),
            Text('Services'),
          ],
        ),
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: Icon(_showInactive ? Icons.visibility : Icons.visibility_off),
            onPressed: () => setState(() => _showInactive = !_showInactive),
          ),
          IconButton(
            icon: Icon(Icons.add),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('Add Service Coming Soon')),
              );
            },
          ),
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _loadServices,
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
                          onPressed: _loadServices,
                          child: Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : filteredServices.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.medical_services, size: 64, color: AppColors.muted),
                          SizedBox(height: 16),
                          Text('No Services', style: TextStyle(fontSize: 18)),
                          SizedBox(height: 8),
                          Text('Add your first service', style: TextStyle(color: AppColors.muted)),
                          SizedBox(height: 16),
                          ElevatedButton(
                            onPressed: () {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('Add Service Coming Soon')),
                              );
                            },
                            child: Text('Add Service'),
                          ),
                        ],
                      ),
                    )
                  : ListView.builder(
                      padding: EdgeInsets.all(8),
                      itemCount: filteredServices.length,
                      itemBuilder: (context, index) {
                        final service = filteredServices[index];
                        return Card(
                          elevation: 1,
                          margin: EdgeInsets.only(bottom: 8),
                          child: ListTile(
                            leading: Container(
                              width: 40,
                              height: 40,
                              decoration: BoxDecoration(
                                color: AppColors.primary.withOpacity(0.1),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Icon(Icons.medical_services, color: AppColors.primary),
                            ),
                            title: Text(service['name'] ?? 'Unknown', style: TextStyle(fontWeight: FontWeight.bold)),
                            subtitle: Text(service['description'] ?? 'No description', maxLines: 2, overflow: TextOverflow.ellipsis),
                            trailing: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text('UGX ', style: TextStyle(fontWeight: FontWeight.bold, color: AppColors.primary)),
                                Text(' min', style: TextStyle(fontSize: 12, color: AppColors.muted)),
                              ],
                            ),
                            isThreeLine: true,
                          ),
                        );
                      },
                    ),
    );
  }
}
