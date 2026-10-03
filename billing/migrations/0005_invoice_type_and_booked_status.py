# Generated manually for booking invoices.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0004_alter_expense_expense_date_alter_invoice_issue_date_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='invoice_type',
            field=models.CharField(
                choices=[('invoice', 'Normal Invoice'), ('booking', 'Booking')],
                db_index=True,
                default='invoice',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Draft'),
                    ('sent', 'Sent'),
                    ('paid', 'Paid'),
                    ('partially_paid', 'Partially Paid'),
                    ('overdue', 'Overdue'),
                    ('booked', 'Booked'),
                    ('cancelled', 'Cancelled'),
                ],
                default='draft',
                max_length=20,
            ),
        ),
    ]
