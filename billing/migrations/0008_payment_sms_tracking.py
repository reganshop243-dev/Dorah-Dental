from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('billing', '0007_invoice_doctor'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='sms_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='payment',
            name='sms_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='sms_error',
            field=models.TextField(blank=True, null=True),
        ),
    ]
