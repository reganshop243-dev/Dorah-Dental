from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0007_mobile_device_token"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameIndex(
                    model_name="usernotification",
                    old_name="notificatio_recipie_5b7ef9_idx",
                    new_name="notificatio_recipie_089876_idx",
                ),
            ],
        ),
    ]