# Generated migration for client_info_manual_make field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0023_add_background_payment_check_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='client_info_manual_make',
            field=models.TextField(
                blank=True,
                null=True,
                help_text='Information displayed to customers when order status is manual_make. Supports HTML formatting.'
            ),
        ),
    ]
