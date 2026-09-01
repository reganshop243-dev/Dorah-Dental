from django.db import migrations, models
from django.core.validators import MinValueValidator, MaxValueValidator


class Migration(migrations.Migration):
    dependencies = [('appointments', '0005_clinicalnote_dentalchart')]

    operations = [
        migrations.AlterField(
            model_name='dentalchart',
            name='tooth_number',
            field=models.PositiveSmallIntegerField(
                help_text='Universal tooth numbering system (1-32)',
                validators=[MinValueValidator(1), MaxValueValidator(32)],
            ),
        ),
        migrations.AddIndex(
            model_name='appointment',
            index=models.Index(fields=['appointment_date', 'doctor', 'status'], name='appt_date_doc_status_idx'),
        ),
        migrations.AddIndex(
            model_name='appointment',
            index=models.Index(fields=['patient', '-appointment_date'], name='appt_patient_date_idx'),
        ),
    ]
