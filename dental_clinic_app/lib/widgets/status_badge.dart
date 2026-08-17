import 'package:flutter/material.dart';

class StatusBadge extends StatelessWidget {
  final String label;
  final String status;

  const StatusBadge({
    Key? key,
    required this.label,
    required this.status,
  }) : super(key: key);

  Color get _color {
    switch (status.toLowerCase()) {
      case 'scheduled':
      case 'active':
      case 'paid':
        return Colors.blue;
      case 'checked_in':
      case 'in_progress':
        return Colors.orange;
      case 'completed':
      case 'sent':
        return Colors.green;
      case 'cancelled':
      case 'no_show':
      case 'failed':
        return Colors.red;
      case 'draft':
        return Colors.grey;
      default:
        return Colors.grey;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: _color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _color.withOpacity(0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          color: _color,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}
