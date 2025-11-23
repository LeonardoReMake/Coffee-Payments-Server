# Generated migration for background payment check feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0022_add_test_status_to_device'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment_started_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Timestamp when user was redirected to payment provider (with timezone)'
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='next_check_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Timestamp for next payment status check (with timezone)'
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='last_check_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Timestamp of last payment status check (with timezone)'
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='check_attempts',
            field=models.IntegerField(
                default=0,
                help_text='Number of payment status check attempts'
            ),
        ),
        migrations.AddField(
            model_name='order',
            name='failed_presentation_desc',
            field=models.TextField(
                blank=True,
                null=True,
                help_text='User-friendly description of failure reason'
            ),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('created', 'Created'),
                    ('pending', 'Pending'),
                    ('paid', 'Paid'),
                    ('not_paid', 'Not Paid'),
                    ('make_pending', 'Make Pending'),
                    ('manual_make', 'Manual Make'),
                    ('successful', 'Successful'),
                    ('failed', 'Failed'),
                    ('make_failed', 'Make Failed'),
                ]
            ),
        ),
    ]
