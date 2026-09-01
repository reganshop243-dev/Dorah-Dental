from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [('appointments', '0006_security_indexes')]
    operations = [
        migrations.AddConstraint(
            model_name='appointment',
            constraint=models.UniqueConstraint(
                condition=Q(('status__in', ['scheduled', 'checked_in', 'in_progress'])),
                fields=('doctor', 'appointment_date', 'appointment_time'),
                name='unique_active_doctor_slot',
            ),
        ),
    ]
