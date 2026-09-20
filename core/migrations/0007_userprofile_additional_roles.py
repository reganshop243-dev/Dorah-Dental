from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_alter_userprofile_otp_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="additional_roles",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
