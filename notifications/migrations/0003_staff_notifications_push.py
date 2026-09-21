from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('notifications','0002_alter_notificationlog_id_and_more')]
    operations = [
        migrations.CreateModel(name='PushSubscription', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('endpoint', models.TextField(unique=True)), ('p256dh', models.CharField(max_length=255)),
            ('auth', models.CharField(max_length=255)), ('user_agent', models.TextField(blank=True)),
            ('created_at', models.DateTimeField(auto_now_add=True)), ('updated_at', models.DateTimeField(auto_now=True)),
            ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='push_subscriptions', to=settings.AUTH_USER_MODEL)),
        ], options={'ordering':['-updated_at']}),
        migrations.CreateModel(name='UserNotification', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('notification_type', models.CharField(choices=[('appointment_assigned','Appointment Assigned'),('appointment_completed','Appointment Completed'),('appointment_updated','Appointment Updated'),('system','System')], default='system', max_length=50)),
            ('title', models.CharField(max_length=200)), ('message', models.TextField()), ('url', models.CharField(blank=True,max_length=500)),
            ('is_read', models.BooleanField(default=False)), ('created_at', models.DateTimeField(auto_now_add=True)), ('read_at', models.DateTimeField(blank=True,null=True)),
            ('appointment', models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.CASCADE,related_name='staff_notifications',to='appointments.appointment')),
            ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='clinic_notifications',to=settings.AUTH_USER_MODEL)),
        ], options={'ordering':['-created_at']}),
        migrations.AddIndex(model_name='usernotification', index=models.Index(fields=['recipient','is_read','-created_at'], name='notificatio_recipie_5d4c2f_idx')),
    ]
