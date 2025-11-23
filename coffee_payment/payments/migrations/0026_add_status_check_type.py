# Generated migration for adding status_check_type field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0025_add_background_check_index'),
    ]

    operations = [
        # Add status_check_type field to MerchantCredentials
        migrations.AddField(
            model_name='merchantcredentials',
            name='status_check_type',
            field=models.CharField(
                choices=[('polling', 'Polling'), ('webhook', 'Webhook'), ('none', 'None')],
                default='polling',
                help_text='Type of payment status check: polling (background check), webhook (notification from payment provider), or none (no automatic check)',
                max_length=20
            ),
        ),
        # Add status_check_type field to Order
        migrations.AddField(
            model_name='order',
            name='status_check_type',
            field=models.CharField(
                blank=True,
                choices=[('polling', 'Polling'), ('webhook', 'Webhook'), ('none', 'None')],
                help_text='Type of payment status check for this order (fixed at creation time)',
                max_length=20,
                null=True
            ),
        ),
        # Backfill existing Orders with 'polling' for consistency
        migrations.RunSQL(
            sql="UPDATE payments_order SET status_check_type = 'polling' WHERE status_check_type IS NULL;",
            reverse_sql="UPDATE payments_order SET status_check_type = NULL;"
        ),
        # Add composite index for efficient Celery task filtering
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status', 'status_check_type', 'next_check_at'], name='payments_or_status_idx'),
        ),
    ]
