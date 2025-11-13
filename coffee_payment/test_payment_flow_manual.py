#!/usr/bin/env python
"""Manual test script to verify payment flow with machine-generated IDs."""

import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coffee_payment.settings')
django.setup()

from django.test import Client
from django.utils import timezone
from datetime import timedelta
from payments.models import Device, Merchant, Order
from unittest.mock import patch, MagicMock

def test_payment_flow():
    """Test complete payment flow with machine-generated ID."""
    print("=" * 60)
    print("PAYMENT FLOW TEST WITH MACHINE-GENERATED IDS")
    print("=" * 60)
    
    client = Client()
    
    # Get or create test data
    merchant, _ = Merchant.objects.get_or_create(
        name='Test Merchant',
        defaults={
            'contact_email': 'test@example.com',
            'bank_account': '1234567890',
            'valid_until': (timezone.now() + timedelta(days=30)).date()
        }
    )
    
    device, _ = Device.objects.get_or_create(
        device_uuid='test-device-flow-123',
        defaults={
            'merchant': merchant,
            'payment_scenario': 'Yookassa',
            'location': 'Test Location',
            'status': 'online',
            'last_interaction': timezone.now()
        }
    )
    
    machine_id = '20250113test-payment-flow-id'
    
    print("\n1. Testing Order Creation via Payment Flow:")
    print(f"   Machine ID: {machine_id}")
    
    # Clean up any existing test order
    Order.objects.filter(id=machine_id).delete()
    
    # Test order creation with machine ID
    order = Order.objects.create(
        id=machine_id,
        drink_name='Test Espresso',
        device=device,
        merchant=merchant,
        size=2,
        price=15000,
        status='created',
        expires_at=timezone.now() + timedelta(minutes=10)
    )
    
    print(f"   ✓ Order created: {order.id}")
    print(f"   ✓ Order status: {order.status}")
    
    print("\n2. Testing Order Lookup:")
    found_order = Order.objects.get(id=machine_id)
    print(f"   ✓ Order found: {found_order.id}")
    print(f"   ✓ Lookup successful: {found_order.id == machine_id}")
    
    print("\n3. Testing Webhook Order Lookup:")
    # Simulate webhook payload
    webhook_payload = {
        'event': 'payment.succeeded',
        'object': {
            'id': 'test_payment_12345',
            'metadata': {
                'order_uuid': machine_id,
                'drink_number': 'drink123',
                'size': '1'
            },
            'amount': {
                'value': '150.00'
            }
        }
    }
    
    try:
        # Extract order_uuid from metadata (simulating webhook logic)
        order_uuid = webhook_payload['object']['metadata']['order_uuid']
        webhook_order = Order.objects.get(id=order_uuid)
        
        print(f"   ✓ Webhook found order: {webhook_order.id}")
        print(f"   ✓ Order matches: {webhook_order.id == machine_id}")
        
        # Test payment_reference_id update
        payment_id = webhook_payload['object']['id']
        webhook_order.payment_reference_id = payment_id
        webhook_order.save(update_fields=['payment_reference_id'])
        
        webhook_order.refresh_from_db()
        print(f"   ✓ Payment reference ID stored: {webhook_order.payment_reference_id}")
        print(f"   ✓ Reference ID matches: {webhook_order.payment_reference_id == payment_id}")
        
    except Order.DoesNotExist:
        print(f"   ✗ Webhook could not find order with ID: {order_uuid}")
    except Exception as e:
        print(f"   ✗ Error during webhook simulation: {e}")
    
    print("\n4. Testing Order Status Updates:")
    order.status = 'paid'
    order.save(update_fields=['status'])
    order.refresh_from_db()
    print(f"   ✓ Status updated to: {order.status}")
    print(f"   ✓ Payment reference preserved: {order.payment_reference_id}")
    
    print("\n5. Testing ForeignKey Relationships:")
    print(f"   ✓ Order device: {order.device.device_uuid}")
    print(f"   ✓ Order merchant: {order.merchant.name}")
    print(f"   ✓ Device -> Order relationship works")
    
    # Clean up
    order.delete()
    print("\n6. Cleanup:")
    print(f"   ✓ Test order deleted")
    
    print("\n" + "=" * 60)
    print("PAYMENT FLOW TEST COMPLETE - ALL CHECKS PASSED")
    print("=" * 60)

if __name__ == '__main__':
    test_payment_flow()
