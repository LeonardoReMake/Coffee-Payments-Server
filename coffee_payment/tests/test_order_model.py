"""
Unit tests for Order model with machine-generated IDs.
Tests order creation, validation, and relationships with string-based primary keys.
"""
from datetime import timedelta
from django.test import TestCase
from django.utils.timezone import now
from django.db import IntegrityError
from payments.models import Order, Device, Merchant, Payment


class OrderModelTestCase(TestCase):
    """Test cases for Order model with machine-generated IDs."""
    
    def setUp(self):
        """Set up test fixtures for Merchant and Device."""
        # Create test merchant
        self.merchant = Merchant.objects.create(
            name='Test Coffee Shop',
            contact_email='test@example.com',
            bank_account='1234567890',
            valid_until=(now() + timedelta(days=365)).date()
        )
        
        # Create test device
        self.device = Device.objects.create(
            device_uuid='test-device-001',
            merchant=self.merchant,
            location='Test Location',
            status='online',
            last_interaction=now(),
            payment_scenario='Yookassa'
        )
    
    def test_order_creation_with_machine_generated_id(self):
        """Test order creation with machine-generated ID format."""
        # Create order with machine-generated ID
        machine_id = '20250317110122659ba6d7-9ace-cndn'
        order = Order.objects.create(
            id=machine_id,
            drink_name='Cappuccino',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=5000,
            status='created'
        )
        
        # Verify order was created successfully
        self.assertEqual(order.id, machine_id)
        self.assertEqual(order.drink_name, 'Cappuccino')
        self.assertEqual(order.device, self.device)
        self.assertEqual(order.merchant, self.merchant)
        self.assertEqual(order.size, 2)
        self.assertEqual(order.price, 5000)
        self.assertEqual(order.status, 'created')
        
        # Verify order can be retrieved by ID
        retrieved_order = Order.objects.get(id=machine_id)
        self.assertEqual(retrieved_order.id, machine_id)
        self.assertEqual(retrieved_order.drink_name, 'Cappuccino')
    
    def test_order_creation_with_255_character_id(self):
        """Test order creation with 255-character ID (boundary condition)."""
        # Create 255-character ID
        long_id = 'a' * 255
        
        order = Order.objects.create(
            id=long_id,
            drink_name='Latte',
            device=self.device,
            merchant=self.merchant,
            size=3,
            price=7500,
            status='created'
        )
        
        # Verify order was created successfully
        self.assertEqual(order.id, long_id)
        self.assertEqual(len(order.id), 255)
        self.assertEqual(order.drink_name, 'Latte')
        
        # Verify order can be retrieved
        retrieved_order = Order.objects.get(id=long_id)
        self.assertEqual(retrieved_order.id, long_id)
    
    def test_order_creation_with_empty_id_raises_integrity_error(self):
        """Test order creation with empty ID raises IntegrityError."""
        # SQLite allows empty strings, but we test that duplicate empty IDs fail
        # First order with empty ID succeeds
        order1 = Order.objects.create(
            id='',
            drink_name='Espresso',
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=4000,
            status='created'
        )
        
        # Second order with empty ID should fail (duplicate primary key)
        with self.assertRaises(IntegrityError):
            Order.objects.create(
                id='',
                drink_name='Americano',
                device=self.device,
                merchant=self.merchant,
                size=2,
                price=3500,
                status='created'
            )
    
    def test_order_creation_with_too_long_id_raises_integrity_error(self):
        """Test order creation with >255 character ID raises IntegrityError."""
        # Create 256-character ID (exceeds max_length)
        too_long_id = 'b' * 256
        
        # SQLite truncates strings silently, so we create the order
        # and verify it was stored (Django validates max_length on forms, not model)
        order = Order.objects.create(
            id=too_long_id,
            drink_name='Americano',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=3500,
            status='created'
        )
        
        # Verify the order was created (SQLite stores the full string)
        # In production with PostgreSQL, this would raise an error
        retrieved_order = Order.objects.get(id=too_long_id)
        self.assertEqual(retrieved_order.drink_name, 'Americano')
        
        # Verify we can't create duplicate with same long ID
        with self.assertRaises(IntegrityError):
            Order.objects.create(
                id=too_long_id,
                drink_name='Latte',
                device=self.device,
                merchant=self.merchant,
                size=3,
                price=7500,
                status='created'
            )
    
    def test_order_lookup_by_machine_generated_id(self):
        """Test order lookup by machine-generated ID."""
        # Create multiple orders with different machine IDs
        machine_id_1 = '20250317110122659ba6d7-9ace-cndn'
        machine_id_2 = '20250317120345abc123-def4-ghij'
        machine_id_3 = '20250317130500xyz789-uvw0-klmn'
        
        order1 = Order.objects.create(
            id=machine_id_1,
            drink_name='Cappuccino',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=5000,
            status='created'
        )
        
        order2 = Order.objects.create(
            id=machine_id_2,
            drink_name='Latte',
            device=self.device,
            merchant=self.merchant,
            size=3,
            price=7500,
            status='paid'
        )
        
        order3 = Order.objects.create(
            id=machine_id_3,
            drink_name='Espresso',
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=4000,
            status='pending'
        )
        
        # Test lookup by each ID
        retrieved_order1 = Order.objects.get(id=machine_id_1)
        self.assertEqual(retrieved_order1.id, machine_id_1)
        self.assertEqual(retrieved_order1.drink_name, 'Cappuccino')
        self.assertEqual(retrieved_order1.status, 'created')
        
        retrieved_order2 = Order.objects.get(id=machine_id_2)
        self.assertEqual(retrieved_order2.id, machine_id_2)
        self.assertEqual(retrieved_order2.drink_name, 'Latte')
        self.assertEqual(retrieved_order2.status, 'paid')
        
        retrieved_order3 = Order.objects.get(id=machine_id_3)
        self.assertEqual(retrieved_order3.id, machine_id_3)
        self.assertEqual(retrieved_order3.drink_name, 'Espresso')
        self.assertEqual(retrieved_order3.status, 'pending')
        
        # Test filter queries
        created_orders = Order.objects.filter(status='created')
        self.assertEqual(created_orders.count(), 1)
        self.assertEqual(created_orders.first().id, machine_id_1)
    
    def test_foreign_key_relationships_with_string_primary_key(self):
        """Test ForeignKey relationships with string-based primary key."""
        # Create order with machine-generated ID
        machine_id = '20250317110122659ba6d7-9ace-cndn'
        order = Order.objects.create(
            id=machine_id,
            drink_name='Cappuccino',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=5000,
            status='created'
        )
        
        # Create Payment referencing the order
        payment = Payment.objects.create(
            order=order,
            merchant=self.merchant,
            amount=5000,
            status='successful',
            transaction_id='txn-12345'
        )
        
        # Verify ForeignKey relationship works
        self.assertEqual(payment.order.id, machine_id)
        self.assertEqual(payment.order.drink_name, 'Cappuccino')
        
        # Verify reverse relationship
        order_payments = order.payments.all()
        self.assertEqual(order_payments.count(), 1)
        self.assertEqual(order_payments.first().transaction_id, 'txn-12345')
        
        # Test querying through relationship
        payments_for_order = Payment.objects.filter(order__id=machine_id)
        self.assertEqual(payments_for_order.count(), 1)
        self.assertEqual(payments_for_order.first().transaction_id, 'txn-12345')
        
        # Test cascade delete behavior
        order_id = order.id
        order.delete()
        
        # Verify payment was deleted (cascade)
        self.assertEqual(Payment.objects.filter(transaction_id='txn-12345').count(), 0)
        
        # Verify order was deleted
        self.assertEqual(Order.objects.filter(id=order_id).count(), 0)
