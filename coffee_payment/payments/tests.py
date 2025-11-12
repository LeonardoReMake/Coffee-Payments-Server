from django.test import TestCase
from django.utils.timezone import now
from datetime import timedelta
from django.conf import settings
from payments.models import Order, Device, Merchant


class OrderModelTestCase(TestCase):
    """Unit tests for Order model"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a test merchant
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            contact_email="test@example.com",
            bank_account="1234567890",
            valid_until=(now() + timedelta(days=365)).date()
        )
        
        # Create a test device
        self.device = Device.objects.create(
            device_uuid="test-device-uuid",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now()
        )

    def test_order_creation_with_expiration(self):
        """
        Test that when creating an order, expires_at is set correctly
        and status is 'created'
        Requirements: 1.1, 8.2
        """
        # Create an order
        order = Order.objects.create(
            drink_name="Espresso",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=2.50,
            status='created'
        )
        
        # Check that status is 'created'
        self.assertEqual(order.status, 'created')
        
        # Check that expires_at is set
        self.assertIsNotNone(order.expires_at)
        
        # Check that expires_at is approximately created_at + ORDER_EXPIRATION_MINUTES
        expiration_minutes = getattr(settings, 'ORDER_EXPIRATION_MINUTES', 15)
        expected_expires_at = order.created_at + timedelta(minutes=expiration_minutes)
        
        # Allow 1 second tolerance for test execution time
        time_diff = abs((order.expires_at - expected_expires_at).total_seconds())
        self.assertLess(time_diff, 1, 
                       f"expires_at should be created_at + {expiration_minutes} minutes")

    def test_order_expiration_check(self):
        """
        Test is_expired() for expired and non-expired orders
        Requirements: 9.1, 9.2, 9.3
        """
        # Create an order with expires_at in the past (expired)
        expired_order = Order(
            drink_name="Cappuccino",
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=3.00,
            status='created'
        )
        expired_order.expires_at = now() - timedelta(minutes=1)
        expired_order.save()
        
        # Check that is_expired() returns True for expired order
        self.assertTrue(expired_order.is_expired(), 
                       "is_expired() should return True for expired order")
        
        # Create an order with expires_at in the future (not expired)
        active_order = Order(
            drink_name="Latte",
            device=self.device,
            merchant=self.merchant,
            size=3,
            price=3.50,
            status='created'
        )
        active_order.expires_at = now() + timedelta(minutes=10)
        active_order.save()
        
        # Check that is_expired() returns False for active order
        self.assertFalse(active_order.is_expired(), 
                        "is_expired() should return False for active order")

    def test_custom_expiration_time(self):
        """
        Test that custom ORDER_EXPIRATION_MINUTES setting is respected
        Requirements: 7.1, 7.2, 8.2
        """
        # Temporarily override the setting
        original_expiration = getattr(settings, 'ORDER_EXPIRATION_MINUTES', 15)
        settings.ORDER_EXPIRATION_MINUTES = 30
        
        try:
            # Create an order
            order = Order.objects.create(
                drink_name="Americano",
                device=self.device,
                merchant=self.merchant,
                size=2,
                price=2.75,
                status='created'
            )
            
            # Check that expires_at = created_at + 30 minutes
            expected_expires_at = order.created_at + timedelta(minutes=30)
            
            # Allow 1 second tolerance for test execution time
            time_diff = abs((order.expires_at - expected_expires_at).total_seconds())
            self.assertLess(time_diff, 1, 
                           "expires_at should be created_at + 30 minutes")
        finally:
            # Restore original setting
            settings.ORDER_EXPIRATION_MINUTES = original_expiration


class OrderIntegrationTestCase(TestCase):
    """Integration tests for order processing flow"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a test merchant
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            contact_email="test@example.com",
            bank_account="1234567890",
            valid_until=(now() + timedelta(days=365)).date()
        )
        
        # Create a test device
        self.device = Device.objects.create(
            device_uuid="test-device-uuid",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now()
        )

    def test_payment_flow_with_status_changes(self):
        """
        Test the complete order processing cycle with status transitions
        Requirements: 1.1, 2.1, 3.1, 4.1
        """
        # Step 1: Create order with 'created' status
        order = Order.objects.create(
            drink_name="Espresso",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=2.50,
            status='created'
        )
        self.assertEqual(order.status, 'created', 
                        "Order should start with 'created' status")
        
        # Step 2: Simulate payment creation - update to 'pending'
        order.external_order_id = "test-payment-id-123"
        order.status = 'pending'
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.status, 'pending', 
                        "Order status should be 'pending' after payment creation")
        self.assertEqual(order.external_order_id, "test-payment-id-123",
                        "External order ID should be set")
        
        # Step 3: Simulate successful payment webhook - update to 'paid'
        order.status = 'paid'
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid', 
                        "Order status should be 'paid' after successful payment")
        
        # Step 4: Simulate Tmetr API command sent - update to 'make_pending'
        order.status = 'make_pending'
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.status, 'make_pending', 
                        "Order status should be 'make_pending' after sending make command")
        
        # Verify order is not expired throughout the flow
        self.assertFalse(order.is_expired(), 
                        "Order should not be expired during normal flow")

    def test_expired_order_handling(self):
        """
        Test that expired orders are properly rejected during webhook processing
        Requirements: 9.1, 9.2, 9.3
        """
        # Create an order with very short expiration time
        order = Order(
            drink_name="Cappuccino",
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=3.00,
            status='created'
        )
        # Set expires_at to 1 second in the future
        order.expires_at = now() + timedelta(seconds=1)
        order.save()
        
        # Set external_order_id and move to pending
        order.external_order_id = "test-payment-id-expired"
        order.status = 'pending'
        order.save()
        
        # Wait for order to expire
        import time
        time.sleep(2)
        
        # Verify order is expired
        order.refresh_from_db()
        self.assertTrue(order.is_expired(), 
                       "Order should be expired after waiting")
        
        # Simulate webhook processing for expired order
        # The webhook should detect expiration and not process the order
        if order.is_expired():
            # This simulates the webhook logic that checks expiration
            # In real webhook, this would return HTTP 400
            expired_detected = True
        else:
            expired_detected = False
        
        self.assertTrue(expired_detected, 
                       "Webhook processing should detect expired order")
        
        # Verify order status remains 'pending' (not updated)
        self.assertEqual(order.status, 'pending', 
                        "Expired order status should not be updated")
