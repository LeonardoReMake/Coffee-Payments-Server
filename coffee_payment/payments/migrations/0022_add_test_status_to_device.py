# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0021_fix_receipt_order_id_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='status',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('online', 'Online'),
                    ('offline', 'Offline'),
                    ('error', 'Error'),
                    ('test', 'Test')
                ]
            ),
        ),
    ]
