import 'package:flutter/material.dart';

class Appointment {
  final int id;
  final int patient;
  final String patientName;
  final String patientPhone;
  final int doctor;
  final String doctorName;
  final int service;
  final String serviceName;
  final double servicePrice;
  final String appointmentDate;
  final String appointmentTime;
  final String status;
  final String? notes;
  final String? diagnosis;
  final String? consultationNotes;
  final String? treatmentPlan;
  final String? prescription;
  final double? treatmentCost;
  final String? referredTo;
  final String? followUpDate;
  final String? followUpNotes;
  final bool sendReminder;
  final bool reminderSent;
  final String createdAt;
  final String? notificationEmail;
  final String? notificationPhone;
  
  Appointment({
    required this.id,
    required this.patient,
    required this.patientName,
    required this.patientPhone,
    required this.doctor,
    required this.doctorName,
    required this.service,
    required this.serviceName,
    required this.servicePrice,
    required this.appointmentDate,
    required this.appointmentTime,
    required this.status,
    this.notes,
    this.diagnosis,
    this.consultationNotes,
    this.treatmentPlan,
    this.prescription,
    this.treatmentCost,
    this.referredTo,
    this.followUpDate,
    this.followUpNotes,
    this.sendReminder = false,
    this.reminderSent = false,
    required this.createdAt,
    this.notificationEmail,
    this.notificationPhone,
  });
  
  String get statusDisplay {
    switch (status) {
      case 'scheduled': return 'Scheduled';
      case 'checked_in': return 'Checked In';
      case 'in_progress': return 'In Progress';
      case 'completed': return 'Completed';
      case 'cancelled': return 'Cancelled';
      case 'no_show': return 'No Show';
      default: return status;
    }
  }
  
  Color get statusColor {
    switch (status) {
      case 'scheduled': return Colors.blue;
      case 'checked_in': return Colors.green;
      case 'in_progress': return Colors.orange;
      case 'completed': return Colors.teal;
      case 'cancelled': return Colors.red;
      case 'no_show': return Colors.grey;
      default: return Colors.grey;
    }
  }
  
  factory Appointment.fromJson(Map<String, dynamic> json) {
    return Appointment(
      id: json['id'] ?? 0,
      patient: json['patient'] ?? 0,
      patientName: json['patient_name'] ?? '',
      patientPhone: json['patient_phone'] ?? '',
      doctor: json['doctor'] ?? 0,
      doctorName: json['doctor_name'] ?? '',
      service: json['service'] ?? 0,
      serviceName: json['service_name'] ?? '',
      servicePrice: (json['service_price'] ?? 0).toDouble(),
      appointmentDate: json['appointment_date'] ?? '',
      appointmentTime: json['appointment_time'] ?? '',
      status: json['status'] ?? 'scheduled',
      notes: json['notes'],
      diagnosis: json['diagnosis'],
      consultationNotes: json['consultation_notes'],
      treatmentPlan: json['treatment_plan'],
      prescription: json['prescription'],
      treatmentCost: json['treatment_cost']?.toDouble(),
      referredTo: json['referred_to'],
      followUpDate: json['follow_up_date'],
      followUpNotes: json['follow_up_notes'],
      sendReminder: json['send_reminder'] ?? false,
      reminderSent: json['reminder_sent'] ?? false,
      createdAt: json['created_at'] ?? '',
      notificationEmail: json['notification_email'],
      notificationPhone: json['notification_phone'],
    );
  }
}
