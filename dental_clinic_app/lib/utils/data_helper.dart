class DataHelper {
  static List<dynamic> safeGetList(dynamic response) {
    if (response == null) return [];
    if (response is List) return response;
    if (response is Map) {
      if (response.containsKey('results')) {
        return response['results'] ?? [];
      }
      if (response.containsKey('data')) {
        return response['data'] ?? [];
      }
      // Check if any key has a list value
      for (var key in response.keys) {
        if (response[key] is List) {
          return response[key];
        }
      }
    }
    return [];
  }
  
  static Map<String, dynamic> safeGetMap(dynamic response) {
    if (response == null) return {};
    if (response is Map) return Map<String, dynamic>.from(response);
    return {};
  }
}
