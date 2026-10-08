from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('patient_portal', '0004_rename_patient_por_patient_1f8a10_idx_patient_por_patient_5b144f_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='PortalDentalTip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('image', models.ImageField(blank=True, null=True, upload_to='portal/dental-tips/')),
                ('is_published', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Dental Tip',
                'verbose_name_plural': 'Dental Tips',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='portaldentaltip',
            index=models.Index(fields=['is_published', '-created_at'], name='patient_por_is_publ_dental_idx'),
        ),
    ]
