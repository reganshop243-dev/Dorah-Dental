from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('core', '0004_alter_companysettings_id_alter_userprofile_id')]
    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='otp_verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
