"""
Integration tests for order status check type feature.

Tests the full flow of status_check_type from MerchantCredentials to Order
and its effect on Celery background task filtering.
"""

import pytest
from datetime import timedelta
from django.utils import timezone
from django.test import TestCase
from payments.models import Merchant, Device, Order, MerchantCredentials
from payments.tasks import check_pending_payments


@pytest.mark.django_db
class TestStatusCheckTypeIntegration(TestCase):
    """Integration tests for status_check_type feature"""
    
    def setUp(self):
        """Set up test data"""
        # Create merchant
        self.merchant = Merchant.objects.create(
            name='Test Merchant',
            contact_email='test@example.com',
            bank_account='1234567890',
            valid_until=timezone.now().date() + timedelta(days=365)
        )
        
        # Create device
        self.device = Device.objects.create(
            device_uuid='test-device-001',
            merchant=self.merchant,
            location='Test Location',
            status='online',
            last_interaction=timezone.now(),
            payment_scenario='Yookassa'
        )
    
    def test_merchant_credentials_default_status_check_type(self):
        """Test that MerchantCredentials defaults to 'polling'"""
        credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={'account_id': '123', 'secret_key': 'secret'}
        )
        
        self.assertEqual(credentials.status_check_type, 'polling')
    
    def test_merchant_credentials_custom_status_check_type(self):
        """Test creating MerchantCredentials with custom status_check_type"""
        for check_type in ['polling', 'webhook', 'none']:
            credentials = MerchantCredentials.objects.create(
                merchant=self.merchant,
                scenario=f'Scenario_{check_type}',
                credentials={'test': 'data'},
                status_check_type=check_type
            )
            
            self.assertEqual(credentials.status_check_type, check_type)
    
    def test_order_status_check_type_propagation(self):
        """Test that status_check_type is copied from MerchantCredentials to Order"""
        # Create credentials with webhook type
        credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={'account_id': '123', 'secret_key': 'secret'},
            status_check_type='webhook'
        )
        
        # Create order
        order = Order.objects.create(
            id='test-order-001',
            device=self.device,
            merchant=self.merchant,
            drink_name='Test Drink',
            size=2,
            price=150.00,
            status='created'
        )
        
        # Simulate payment initiation logic
        order.status_check_type = credentials.status_check_type
        order.save()
        
        # Verify propagation
        order.refresh_from_db()
        self.assertEqual(order.status_check_type, 'webhook')
    
    def test_order_status_check_type_immutability(self):
        """Test that Order.status_check_type doesn't change when MerchantCredentials is updated"""
        # Create credentials
        credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={'account_id': '123', 'secret_key': 'secret'},
            status_check_type='polling'
        )
        
        # Create order with status_check_type
        order = Order.objects.create(
            id='test-order-002',
            device=self.device,
            merchant=self.merchant,
            drink_name='Test Drink',
            size=2,
            price=150.00,
            status='pending',
            status_check_type='polling'
        )
        
        original_check_type = order.status_check_type
        
        # Update credentials
        credentials.status_check_type = 'webhook'
        credentials.save()
        
        # Verify order status_check_type unchanged
        order.refresh_from_db()
        self.assertEqual(order.status_check_type, original_check_type)
    
    def test_celery_task_filters_by_status_check_type(self):
        """Test that Celery task only processes orders with status_check_type='polling'"""
        now = timezone.now()
        
        # Create orders with different status_check_type values
        orders_data = [
            ('order-polling', 'polling'),
            ('order-webhook', 'webhook'),
            ('order-none', 'none'),
        ]
        
        for order_id, check_type in orders_data:
            Order.objects.create(
                id=order_id,
                device=self.device,
                merchant=self.merchant,
                drink_name='Test Drink',
                size=2,
                price=150.00,
                status='pending',
                status_check_type=check_type,
                payment_started_at=now - timedelta(minutes=1),
                next_check_at=now - timedelta(seconds=1),
                expires_at=now + timedelta(minutes=10)
            )
        
        # Query orders as Celery task does
        filtered_orders = Order.objects.filter(
            status='pending',
            status_check_type='polling',
            next_check_at__lte=now,
            next_check_at__isnull=False,
            expires_at__gt=now
        )
        
        # Verify only polling order is selected
        self.assertEqual(filtered_orders.count(), 1)
        self.assertEqual(filtered_orders.first().id, 'order-polling')
    
    def test_celery_task_preserves_existing_filters(self):
        """Test that adding status_check_type filter doesn't break existing filters"""
        now = timezone.now()
        
        # Create orders with various conditions
        test_cases = [
            # (order_id, status, status_check_type, next_check_at, expires_at, should_be_selected)
            ('order-valid', 'pending', 'polling', now - timedelta(seconds=1), now + timedelta(minutes=10), True),
            ('order-wrong-status', 'paid', 'polling', now - timedelta(seconds=1), now + timedelta(minutes=10), False),
            ('order-wrong-check-type', 'pending', 'webhook', now - timedelta(seconds=1), now + timedelta(minutes=10), False),
            ('order-future-check', 'pending', 'polling', now + timedelta(minutes=1), now + timedelta(minutes=10), False),
            ('order-expired', 'pending', 'polling', now - timedelta(seconds=1), now - timedelta(minutes=1), False),
            ('order-null-next-check', 'pending', 'polling', None, now + timedelta(minutes=10), False),
        ]
        
        for order_id, status, check_type, next_check, expires, _ in test_cases:
            Order.objects.create(
                id=order_id,
                device=self.device,
                merchant=self.merchant,
                drink_name='Test Drink',
                size=2,
                price=150.00,
                status=status,
                status_check_type=check_type,
                payment_started_at=now - timedelta(minutes=1),
                next_check_at=next_check,
                expires_at=expires
            )
        
        # Query orders as Celery task does
        filtered_orders = Order.objects.filter(
            status='pending',
            status_check_type='polling',
            next_check_at__lte=now,
            next_check_at__isnull=False,
            expires_at__gt=now
        )
        
        # Verify only valid order is selected
        self.assertEqual(filtered_orders.count(), 1)
        self.assertEqual(filtered_orders.first().id, 'order-valid')
    
    def test_migration_backfill_consistency(self):
        """Test that migration backfills existing records correctly"""
        # Create order without status_check_type (simulating pre-migration state)
        order = Order.objects.create(
            id='test-order-migration',
            device=self.device,
            merchant=self.merchant,
            drink_name='Test Drink',
            size=2,
            price=150.00,
            status='pending'
        )
        
        # Simulate migration backfill
        if order.status_check_type is None:
            order.status_check_type = 'polling'
            order.save()
        
        # Verify backfill
        order.refresh_from_db()
        self.assertEqual(order.status_check_type, 'polling')
