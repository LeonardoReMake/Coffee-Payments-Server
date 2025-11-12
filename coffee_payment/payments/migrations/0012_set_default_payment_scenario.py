# Generated data migration to ensure all existing devices have payment_scenario set

from django.db import migrations


def set_default_payment_scenario(apps, schema_editor):
    """
    Set payment_scenario='Yookassa' for all existing devices.
    This ensures data consistency even though the field has a default value.
    """
    Device = apps.get_model('payments', 'Device')
    
    # Update any devices that might have NULL or empty payment_scenario
    # (though this shouldn't happen due to the default in 0010)
    updated_count = Device.objects.filter(
        payment_scenario__isnull=True
    ).update(payment_scenario='Yookassa')
    
    # Also update any devices with empty string
    updated_count += Device.objects.filter(
        payment_scenario=''
    ).update(payment_scenario='Yookassa')
    
    if updated_count > 0:
        print(f"Updated {updated_count} devices to use Yookassa payment scenario")
    else:
        print("All devices already have payment_scenario set")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration - no action needed as we're just ensuring data consistency
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0011_merchantcredentials'),
    ]

    operations = [
        migrations.RunPython(set_default_payment_scenario, reverse_migration),
    ]
