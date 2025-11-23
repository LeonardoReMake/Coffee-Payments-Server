# Generated migration for background payment check index

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0024_add_client_info_manual_make'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE INDEX IF NOT EXISTS payments_order_background_check_idx 
            ON payments_order (status, next_check_at, expires_at) 
            WHERE status = 'pending' AND next_check_at IS NOT NULL;
            """,
            reverse_sql="DROP INDEX IF EXISTS payments_order_background_check_idx;",
        ),
    ]
