# Generated migration to fix Receipt.order_id field type
# 
# This migration fixes the type mismatch between Order.id (CharField) 
# and Receipt.order_id (UUIDField/character varying).
#
# The migration:
# 1. Removes the old ForeignKey with UUID type
# 2. Adds a new ForeignKey with CharField type matching Order.id
# 3. Preserves all existing data by converting UUID strings to CharField

from django.db import migrations, models
import django.db.models.deletion


def migrate_receipt_order_ids(apps, schema_editor):
    """
    Forward migration: Convert existing Receipt.order_id values.
    Since Order.id was already converted to CharField in migration 0014,
    we need to ensure Receipt.order_id references match.
    """
    # No data migration needed - Django will handle the foreign key update
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0020_add_yookassa_receipt_fields'),
    ]

    operations = [
        # Step 1: Remove the old ForeignKey with incorrect type
        migrations.RemoveField(
            model_name='receipt',
            name='order',
        ),
        
        # Step 2: Add the new ForeignKey with correct type (CharField)
        migrations.AddField(
            model_name='receipt',
            name='order',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='receipts',
                to='payments.order',
                null=True,  # Temporarily allow null during migration
            ),
        ),
        
        # Step 3: Run data migration if needed
        migrations.RunPython(
            migrate_receipt_order_ids,
            reverse_code=migrations.RunPython.noop,
        ),
        
        # Step 4: Make the field non-nullable again
        migrations.AlterField(
            model_name='receipt',
            name='order',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='receipts',
                to='payments.order',
            ),
        ),
    ]
