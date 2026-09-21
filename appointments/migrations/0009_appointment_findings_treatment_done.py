from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('appointments', '0008_rename_appt_date_doc_status_idx_appointment_appoint_d43bd6_idx_and_more')]
    operations = [
        migrations.AddField(model_name='appointment', name='findings', field=models.TextField(blank=True, help_text='Clinical findings recorded when the appointment is completed', null=True)),
        migrations.AddField(model_name='appointment', name='treatment_done', field=models.TextField(blank=True, help_text='Treatment/procedure actually completed', null=True)),
    ]
