"""
Integration tests for unified order status page functionality.
"""
import json
from datetime import timedelta
from django.test import TestCase, Client
from django.utils.timezone import now
from payments.models import Merchant, Device, Order


class UnifiedOrderStatusIntegrationTestCase(TestCase):
    """Integration test cases for unified order status page flow."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test merchant
        self.merchant = Merchant.objects.create(
            name='Test Merchant',
            contact_email='test@example.com',
            bank_account='1234567890',
            valid_until=(now() + timedelta(days=365)).date()
        )
        
        # Create test device
        self.device = Device.objects.create(
            device_uuid='test-device-uuid',
            merchant=self.merchant,
            location='Test Location',
            status='online',
            last_interaction=now(),
            payment_scenario='Yookassa',
            logo_url='https://example.com/logo.png',
            client_info='Test client info'
        )
    
    def test_show_order_status_page_with_valid_order(self):
        """Test that order status page renders successfully with valid order."""
        # Create test order
        order = Order.objects.create(
            id='test-order-uuid',
            drink_name='Americano',
            drink_number='drink-123',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=15000,
            status='created'
        )
        
        # Request order status page
        response = self.client.get(f'/v1/order-status-page?order_id={order.id}')
        
        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Статус заказа')
        self.assertContains(response, order.id)
    
    def test_show_order_status_page_with_invalid_order(self):
        """Test that order status page returns error for non-existent order."""
        # Request order status page with non-existent order
        response = self.client.get('/v1/order-status-page?order_id=nonexistent-order')
        
        # Verify error response
        self.assertEqual(response.status_code, 404)
    
    def test_show_order_status_page_without_order_id(self):
        """Test that order status page returns error when order_id is missing."""
        # Request order status page without order_id parameter
        response = self.client.get('/v1/order-status-page')
        
        # Verify error response
        self.assertEqual(response.status_code, 400)
    
    def test_status_page_polling_detects_status_change(self):
        """Test that polling detects order status changes."""
        # Create test order with 'created' status
        order = Order.objects.create(
            id='test-order-uuid',
            drink_name='Americano',
            drink_number='drink-123',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=15000,
            status='created'
        )
        
        # First API call - should return 'created' status
        response1 = self.client.get(f'/v1/order-status/{order.id}')
        self.assertEqual(response1.status_code, 200)
        data1 = json.loads(response1.content)
        self.assertEqual(data1['status'], 'created')
        
        # Update order status
        order.status = 'pending'
        order.save()
        
        # Second API call - should return 'pending' status
        response2 = self.client.get(f'/v1/order-status/{order.id}')
        self.assertEqual(response2.status_code, 200)
        data2 = json.loads(response2.content)
        self.assertEqual(data2['status'], 'pending')
    
    def test_expired_order_handling(self):
        """Test that expired orders are handled correctly."""
        # Create test order with expired time
        order = Order.objects.create(
            id='test-order-uuid',
            drink_name='Americano',
            drink_number='drink-123',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=15000,
            status='created',
            expires_at=now() - timedelta(minutes=1)  # Expired 1 minute ago
        )
        
        # Request order status
        response = self.client.get(f'/v1/order-status/{order.id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        
        # Verify that expires_at is in the past
        from datetime import datetime
        expires_at = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        self.assertLess(expires_at, datetime.now(expires_at.tzinfo))
    
    def test_initiate_payment_with_expired_order(self):
        """Test that initiate_payment returns error for expired order."""
        # Create test order with expired time
        order = Order.objects.create(
            id='test-order-uuid',
            drink_name='Americano',
            drink_number='drink-123',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=15000,
            status='created',
            expires_at=now() - timedelta(minutes=1)
        )
        
        # Try to initiate payment
        response = self.client.post(
            '/v1/initiate-payment',
            data=json.dumps({'order_id': order.id}),
            content_type='application/json'
        )
        
        # Verify error response
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
