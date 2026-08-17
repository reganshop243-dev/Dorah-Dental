class DashboardStats {
  final int totalPatients;
  final int totalAppointmentsToday;
  final int totalAppointments;
  final int totalServices;
  final int totalDoctors;
  final int totalInvoices;
  final double revenueToday;
  
  DashboardStats({
    required this.totalPatients,
    required this.totalAppointmentsToday,
    required this.totalAppointments,
    required this.totalServices,
    required this.totalDoctors,
    required this.totalInvoices,
    required this.revenueToday,
  });
  
  factory DashboardStats.fromJson(Map<String, dynamic> json) {
    return DashboardStats(
      totalPatients: json['total_patients'] ?? 0,
      totalAppointmentsToday: json['total_appointments_today'] ?? 0,
      totalAppointments: json['total_appointments'] ?? 0,
      totalServices: json['total_services'] ?? 0,
      totalDoctors: json['total_doctors'] ?? 0,
      totalInvoices: json['total_invoices'] ?? 0,
      revenueToday: (json['revenue_today'] ?? 0).toDouble(),
    );
  }
}
