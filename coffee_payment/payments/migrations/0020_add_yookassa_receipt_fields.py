# Generated manually for yookassa-receipt-scenario

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0019_add_make_failed_status'),
    ]

    operations = [
        # Add meta field to Drink model
        migrations.AddField(
            model_name='drink',
            name='meta',
            field=models.JSONField(
                blank=True,
                null=True,
                help_text='Receipt metadata in JSON format. Example: {"vat_code": 2, "measure": "piece", "payment_subject": "commodity", "payment_mode": "full_payment"}'
            ),
        ),
        
        # Change Drink ID from UUID to Integer
        # Note: This is a destructive operation that will require data migration
        # For MVP, we'll handle this separately if needed
        migrations.AlterField(
            model_name='drink',
            name='id',
            field=models.IntegerField(primary_key=True, serialize=False),
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
