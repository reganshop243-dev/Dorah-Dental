from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('appointments', '0008_rename_appt_date_doc_status_idx_appointment_appoint_d43bd6_idx_and_more'),
        ('patient_portal', '0002_hash_portal_pins'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='PortalOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('image', models.ImageField(blank=True, null=True, upload_to='portal/offers/')),
                ('valid_from', models.DateField(blank=True, null=True)),
                ('valid_until', models.DateField(blank=True, null=True)),
                ('is_published', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='PatientConversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(default='General enquiry', max_length=200)),
                ('status', models.CharField(choices=[('open', 'Open'), ('closed', 'Closed')], default='open', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('doctor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='portal_conversations', to='appointments.doctor')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='portal_conversations', to='patients.patient')),
            ],
            options={'ordering': ['-updated_at']},
        ),
        migrations.CreateModel(
            name='PatientMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sender_type', models.CharField(choices=[('patient', 'Patient'), ('staff', 'Clinic/Doctor')], default='patient', max_length=10)),
                ('body', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='patient_portal.patientconversation')),
                ('sender', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='patient_portal_messages', to='auth.user')),
            ],
            options={'ordering': ['created_at']},
        ),
        migrations.CreateModel(
            name='PortalNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(choices=[('appointment', 'Appointment'), ('payment', 'Payment'), ('message', 'Message'), ('offer', 'Offer'), ('clinic', 'Clinic Announcement'), ('system', 'System')], default='system', max_length=20)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('url', models.CharField(blank=True, default='', max_length=500)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('appointment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='portal_notifications', to='appointments.appointment')),
                ('conversation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='portal_notifications', to='patient_portal.patientconversation')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='portal_notifications', to='patients.patient')),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.AddIndex(model_name='portaloffer', index=models.Index(fields=['is_published', 'valid_from', 'valid_until'], name='patient_por_is_publ_1e5b9e_idx')),
        migrations.AddIndex(model_name='patientconversation', index=models.Index(fields=['patient', 'status', '-updated_at'], name='patient_por_patient_1f8a10_idx')),
        migrations.AddIndex(model_name='patientmessage', index=models.Index(fields=['conversation', 'created_at'], name='patient_por_convers_3f4a2c_idx')),
        migrations.AddIndex(model_name='patientmessage', index=models.Index(fields=['sender_type', 'read_at'], name='patient_por_sender__9d3f91_idx')),
        migrations.AddIndex(model_name='portalnotification', index=models.Index(fields=['patient', 'is_read', '-created_at'], name='patient_por_patient_8b1d31_idx')),
        migrations.AddIndex(model_name='portalnotification', index=models.Index(fields=['appointment', 'notification_type'], name='patient_por_appointm_4e7a22_idx')),
    ]
