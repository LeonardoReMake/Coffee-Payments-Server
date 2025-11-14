# Generated manually for adding drink_number field to Order model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0016_update_client_error_info_help_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='drink_number',
            field=models.CharField(
                blank=True,
                help_text='Drink ID at the device (drinkNo from QR code)',
                max_length=255,
                null=True
            ),
        ),
    ]
