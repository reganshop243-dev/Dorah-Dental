from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
    dependencies=[('notifications','0006_rename_notificatio_recipie_5b7ef9_idx_notificatio_recipie_089876_idx'),('patients','0009_rename_patients_pat_patient_1e4a62_idx_patients_pa_patient_59e50b_idx_and_more')]
    operations=[migrations.CreateModel(name='MobileDeviceToken',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('token',models.TextField(unique=True)),('platform',models.CharField(default='mobile',max_length=20)),('is_active',models.BooleanField(default=True)),('last_seen',models.DateTimeField(auto_now=True)),('created_at',models.DateTimeField(auto_now_add=True)),('patient',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='mobile_device_tokens',to='patients.patient'))],options={'ordering':['-last_seen']})]
