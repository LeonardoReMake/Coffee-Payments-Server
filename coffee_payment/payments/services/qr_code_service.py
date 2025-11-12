from django.shortcuts import get_object_or_404
from django.http import Http404
from payments.models import Device, Merchant
from datetime import datetime


def validate_device(device_uuid):
    """
    Validates device existence by device_uuid.
    
    This function retrieves a Device instance from the database using the provided
    device_uuid. If the device does not exist, it raises an Http404 exception.
    
    Args:
        device_uuid (str): UUID of the device to validate
        
    Returns:
        Device: Device instance if found
        
    Raises:
        Http404: If device with the given device_uuid does not exist
    """
    device = get_object_or_404(Device, device_uuid=device_uuid)
    return device


def validate_merchant(device):
    """
    Validates merchant permissions for the device.
    
    This function retrieves the Merchant associated with the given Device and
    checks if the merchant's permissions are still valid. The merchant's
    valid_until date must be in the future for the validation to pass.
    
    Args:
        device (Device): Device instance whose merchant needs to be validated
        
    Returns:
        Merchant: Merchant instance if permissions are valid
        
    Raises:
        Http404: If merchant with the given id does not exist
        ValueError: If merchant permissions have expired (valid_until date is in the past)
    """
    merchant = get_object_or_404(Merchant, id=device.merchant_id)
    if hasattr(merchant, 'valid_until') and merchant.valid_until <= datetime.now().date():
        raise ValueError("Merchant permissions expired")
    return merchant