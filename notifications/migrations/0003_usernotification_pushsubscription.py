from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('appointments', '0009_appointment_findings_treatment_done'),
        ('patients', '0008_patientcontactaccessrequest'),
        ('notifications', '0002_alter_notificationlog_id_and_more'),
    ]
    operations = [
        migrations.CreateModel(
            name='PushSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('endpoint', models.URLField(max_length=1000, unique=True)),
                ('p256dh', models.TextField()),
                ('auth', models.TextField()),
                ('user_agent', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='push_subscriptions', to=settings.AUTH_USER_MODEL)),
            ], options={'ordering':['-updated_at']},
        ),
        migrations.CreateModel(
            name='UserNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('appointment_assigned','Appointment Assigned'),('appointment_completed','Appointment Completed'),('contact_access_request','Contact Access Request'),('contact_access_approved','Contact Access Approved'),('contact_access_denied','Contact Access Denied'),('system','System')], default='system', max_length=40)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('url', models.CharField(blank=True, default='', max_length=500)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('appointment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_notifications', to='appointments.appointment')),
                ('patient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_notifications', to='patients.patient')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='clinic_notifications', to=settings.AUTH_USER_MODEL)),
            ], options={'ordering':['-created_at']},
        ),
        migrations.AddIndex(model_name='usernotification', index=models.Index(fields=['recipient','is_read','-created_at'], name='notificatio_recipie_5b7ef9_idx')),
    ]
