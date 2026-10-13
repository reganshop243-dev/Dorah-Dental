# Generated for assigning the treating doctor to an invoice.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0009_appointment_findings_treatment_done'),
        ('billing', '0006_paymenteditlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='doctor',
            field=models.ForeignKey(
                blank=True,
                help_text='Doctor who performed the treatment',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='invoices',
                to='appointments.doctor',
            ),
        ),
    ]
