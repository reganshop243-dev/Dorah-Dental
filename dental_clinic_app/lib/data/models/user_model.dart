class UserModel {
  final int id;
  final String username;
  final String fullName;
  final String role;
  final String phone;
  
  UserModel({
    required this.id,
    required this.username,
    required this.fullName,
    required this.role,
    required this.phone,
  });
  
  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: json['id'] ?? 0,
      username: json['username'] ?? '',
      fullName: json['full_name'] ?? '',
      role: json['role'] ?? 'patient',
      phone: json['phone'] ?? '',
    );
  }
  
  bool get isAdmin => role == 'admin';
  bool get isDoctor => role == 'doctor';
  bool get isReceptionist => role == 'receptionist';
}
