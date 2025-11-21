# Generated manually for yookassa-receipt-scenario

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0019_add_make_failed_status'),
    ]

    operations = [
        # Delete the old Drink model (this will drop the table)
        migrations.DeleteModel(
            name='Drink',
        ),
        
        # Recreate Drink model with string ID and meta field
        migrations.CreateModel(
            name='Drink',
            fields=[
                ('id', models.CharField(primary_key=True, max_length=255, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('prices', models.JSONField()),
                ('available', models.BooleanField(default=True)),
                ('meta', models.JSONField(
                    blank=True,
                    null=True,
                    help_text='Receipt metadata in JSON format. Example: {"vat_code": 2, "measure": "piece", "payment_subject": "commodity", "payment_mode": "full_payment"}'
                )),
            ],
        ),
        
        # Add new fields to Receipt model
        migrations.AddField(
            model_name='receipt',
            name='drink_no',
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                help_text='Drink ID at the device'
            ),
        ),
        migrations.AddField(
            model_name='receipt',
            name='amount',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                help_text='Payment amount in kopecks',
                default=0
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='receipt',
            name='receipt_data',
            field=models.JSONField(
                blank=True,
                null=True,
                help_text='Complete receipt data sent to Yookassa in JSON format'
            ),
        ),
        migrations.AddField(
            model_name='receipt',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
    ]
