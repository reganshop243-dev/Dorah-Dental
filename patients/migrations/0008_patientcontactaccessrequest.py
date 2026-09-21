from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('patients', '0007_patient_user')]
    operations = [
        migrations.CreateModel(
            name='PatientContactAccessRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending','Pending'),('approved','Approved'),('denied','Denied')], default='pending', max_length=20)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contact_access_requests', to='patients.patient')),
                ('requester', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='patient_contact_requests', to=settings.AUTH_USER_MODEL)),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_patient_contact_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering':['-requested_at']},
        ),
        migrations.AddIndex(model_name='patientcontactaccessrequest', index=models.Index(fields=['patient','requester','status'], name='patients_pat_patient_1e4a62_idx')),
        migrations.AddIndex(model_name='patientcontactaccessrequest', index=models.Index(fields=['status','-requested_at'], name='patients_pat_status_0cf65f_idx')),
    ]
