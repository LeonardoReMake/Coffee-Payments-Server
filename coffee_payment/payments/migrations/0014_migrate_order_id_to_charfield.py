# Generated migration for Order ID field type change
# 
# This migration converts the Order model's primary key from UUIDField to CharField
# to support machine-generated order IDs in custom formats.
#
# IMPORTANT: This migration is NOT reversible via Django's automatic rollback.
# If rollback is needed, restore from database backup taken before migration.
#
# The migration:
# 1. Adds a temporary CharField field
# 2. Copies all UUID values to the temporary field as strings
# 3. Removes the old UUID primary key
# 4. Renames the temporary field to 'id' and makes it the primary key
# 5. Renames external_order_id to payment_reference_id
#
# All ForeignKey relationships are automatically updated by Django.

import uuid
from django.db import migrations, models


def copy_uuid_to_temp_field(apps, schema_editor):
    """
    Forward migration: Copy existing UUID values to temporary CharField.
    This preserves all existing order data during the migration.
    """
    Order = apps.get_model('payments', 'Order')
    db_alias = schema_editor.connection.alias
    
    # Convert all existing UUID IDs to string format
    for order in Order.objects.using(db_alias).all():
        order.id_temp = str(order.id)
        order.save(update_fields=['id_temp'])


def copy_string_to_temp_uuid(apps, schema_editor):
    """
    Reverse migration: Copy string IDs to temporary UUID field.
    Only works if all IDs are valid UUIDs.
    """
    Order = apps.get_model('payments', 'Order')
    db_alias = schema_editor.connection.alias
    
    # Convert string IDs back to UUID format
    for order in Order.objects.using(db_alias).all():
        try:
            # Validate that the ID is a valid UUID
            uuid_obj = uuid.UUID(order.id)
            order.id_temp_uuid = uuid_obj
            order.save(update_fields=['id_temp_uuid'])
        except (ValueError, AttributeError):
            # If ID is not a valid UUID, we cannot reverse the migration
            raise ValueError(
                f"Cannot reverse migration: Order {order.id} has non-UUID ID. "
                "Rollback is only possible if all order IDs are valid UUIDs."
            )


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0013_device_client_info_device_logo_url'),
    ]

    operations = [
        # Step 1: Add temporary CharField to store UUID values as strings
        migrations.AddField(
            model_name='order',
            name='id_temp',
            field=models.CharField(max_length=255, null=True),
        ),
        
        # Step 2: Copy all UUID values to temporary field as strings
        migrations.RunPython(
            copy_uuid_to_temp_field,
            reverse_code=migrations.RunPython.noop,
        ),
        
        # Step 3: Remove the old UUID primary key
        # This will temporarily leave the table without a primary key
        migrations.RemoveField(
            model_name='order',
            name='id',
        ),
        
        # Step 4: Rename temporary field to 'id' and make it the primary key
        migrations.RenameField(
            model_name='order',
            old_name='id_temp',
            new_name='id',
        ),
        
        # Step 5: Alter the field to be a proper primary key
        migrations.AlterField(
            model_name='order',
            name='id',
            field=models.CharField(max_length=255, primary_key=True, serialize=False),
        ),
        
        # Step 6: Rename external_order_id to payment_reference_id
        migrations.RenameField(
            model_name='order',
            old_name='external_order_id',
            new_name='payment_reference_id',
        ),
    ]
