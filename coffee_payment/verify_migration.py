#!/usr/bin/env python
"""Script to verify database migration integrity."""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coffee_payment.settings')
django.setup()

from payments.models import Order, Payment, Receipt, TBankPayment

def verify_migration():
    print("=" * 60)
    print("DATABASE MIGRATION VERIFICATION")
    print("=" * 60)
    
    # Check record counts
    print("\n1. Record Counts:")
    print(f"   Total Orders: {Order.objects.count()}")
    print(f"   Total Payments: {Payment.objects.count()}")
    print(f"   Total Receipts: {Receipt.objects.count()}")
    print(f"   Total TBankPayments: {TBankPayment.objects.count()}")
    
    # Check existing orders
    print("\n2. Existing Orders Verification:")
    for order in Order.objects.all():
        print(f"   Order ID: {order.id}")
        print(f"   ID Type: {type(order.id).__name__}")
        print(f"   ID Length: {len(str(order.id))}")
        print(f"   Status: {order.status}")
        print(f"   Drink: {order.drink_name}")
        print()
    
    # Check ForeignKey relationships
    print("3. ForeignKey Relationships:")
    for order in Order.objects.all():
        payments = Payment.objects.filter(order=order)
        receipts = Receipt.objects.filter(order=order)
        
        print(f"   Order {order.id}:")
        print(f"     Related Payments: {payments.count()}")
        if payments.exists():
            for payment in payments:
                print(f"       Payment ID: {payment.id}, Order ID: {payment.order.id}")
        
        print(f"     Related Receipts: {receipts.count()}")
        if receipts.exists():
            for receipt in receipts:
                print(f"       Receipt ID: {receipt.id}, Order ID: {receipt.order.id}")
        print()
    
    # Test order creation with machine-generated ID
    print("4. Test Order Creation with Machine-Generated ID:")
    test_order_id = "20250113120000test-machine-id"
    try:
        from payments.models import Device, Merchant
        device = Device.objects.first()
        merchant = Merchant.objects.first()
        
        if device and merchant:
            test_order = Order.objects.create(
                id=test_order_id,
                drink_name="Test Coffee",
                device=device,
                merchant=merchant,
                size=2,
                price=5.00,
                status='created'
            )
            print(f"   ✓ Successfully created order with ID: {test_order.id}")
            print(f"   ✓ Order ID type: {type(test_order.id).__name__}")
            
            # Test order lookup
            print("\n5. Test Order Lookup:")
            found_order = Order.objects.get(id=test_order_id)
            print(f"   ✓ Successfully retrieved order: {found_order.id}")
            print(f"   ✓ Order matches: {found_order.id == test_order_id}")
            
            # Clean up test order
            test_order.delete()
            print(f"   ✓ Test order cleaned up")
        else:
            print("   ⚠ No device or merchant found, skipping order creation test")
    
    except Exception as e:
        print(f"   ✗ Error creating test order: {e}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    verify_migration()
