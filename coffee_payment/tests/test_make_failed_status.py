"""
Unit tests for make_failed status functionality.
"""
import pytest
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from payments.models import Order, Device, Merchant


class MakeFailedStatusTestCase(TestCase):
    """Test cases for make_failed status in Order model."""
    
    def setUp(self):
        """Set up test data."""
        # Create test merchant
        self.merchant = Merchant.objects.create(
            name='Test Merchant',
            contact_email='test@example.com',
            bank_account='1234567890',
            valid_until=timezone.now().date() + timedelta(days=30)
        )
        
        # Create test device
        self.device = Device.objects.create(
            device_uuid='test-device-uuid',
            merchant=self.merchant,
            location='Test Location',
            status='online',
            last_interaction=timezone.now(),
            payment_scenario='Yookassa'
        )
    
    def test_order_model_make_failed_status(self):
        """Test that make_failed status can be set and saved for an order."""
        # Create order with created status
        order = Order.objects.create(
            id='test-order-123',
            drink_name='Americano',
            drink_number='drink-001',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=15000,
            status='created'
        )
        
        # Update status to make_failed
        order.status = 'make_failed'
        order.save()
        
        # Retrieve order from database
        saved_order = Order.objects.get(id='test-order-123')
        
        # Assert status is make_failed
        self.assertEqual(saved_order.status, 'make_failed')
    
    def test_order_status_choices_include_make_failed(self):
        """Test that make_failed is in the list of valid status choices."""
        # Get status choices from Order model
        status_field = Order._meta.get_field('status')
        status_choices = [choice[0] for choice in status_field.choices]
        
        # Assert make_failed is in choices
        self.assertIn('make_failed', status_choices)



class WebhookErrorHandlingTestCase(TestCase):
    """Test cases for webhook handler error scenarios with make_failed status."""
    
    def setUp(self):
        """Set up test data."""
        from unittest.mock import patch
        
        # Create test merchant
        self.merchant = Merchant.objects.create(
            name='Test Merchant',
            contact_email='test@example.com',
            bank_account='1234567890',
            valid_until=timezone.now().date() + timedelta(days=30)
        )
        
        # Create test device
        self.device = Device.objects.create(
            device_uuid='test-device-uuid',
            merchant=self.merchant,
            location='Test Location',
            status='online',
            last_interaction=timezone.now(),
            payment_scenario='Yookassa'
        )
        
        # Create test order
        self.order = Order.objects.create(
            id='test-order-webhook',
            drink_name='Cappuccino',
            drink_number='drink-002',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=18000,
            status='paid'
        )
    
    @pytest.mark.timeout(30)
    def test_webhook_make_failed_on_tmetr_request_exception(self):
        """Test that order status changes to make_failed on Tmetr API RequestException."""
        from unittest.mock import patch, MagicMock
        import requests
        from django.test import Client
        import json
        
        client = Client()
        
        # Prepare webhook payload
        webhook_payload = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'payment-123',
                'amount': {'value': '180.00'},
                'metadata': {
                    'order_uuid': 'test-order-webhook',
                    'drink_number': 'drink-002',
                    'size': '1'
                }
            }
        }
        
        # Mock TmetrService.send_make_command to raise RequestException
        with patch('payments.views.TmetrService') as mock_tmetr_service:
            mock_instance = MagicMock()
            mock_instance.send_make_command.side_effect = requests.RequestException('Connection timeout')
            mock_tmetr_service.return_value = mock_instance
            
            # Send webhook request
            response = client.post(
                '/v1/yook-pay-webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json'
            )
        
        # Assert response is 200 (not 503)
        self.assertEqual(response.status_code, 200)
        
        # Retrieve order and check status
        order = Order.objects.get(id='test-order-webhook')
        self.assertEqual(order.status, 'make_failed')
    
    @pytest.mark.timeout(30)
    def test_webhook_make_failed_on_unexpected_exception(self):
        """Test that order status changes to make_failed on unexpected Exception."""
        from unittest.mock import patch, MagicMock
        from django.test import Client
        import json
        
        client = Client()
        
        # Reset order status to paid
        self.order.status = 'paid'
        self.order.save()
        
        # Prepare webhook payload
        webhook_payload = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'payment-456',
                'amount': {'value': '180.00'},
                'metadata': {
                    'order_uuid': 'test-order-webhook',
                    'drink_number': 'drink-002',
                    'size': '1'
                }
            }
        }
        
        # Mock TmetrService.send_make_command to raise generic Exception
        with patch('payments.views.TmetrService') as mock_tmetr_service:
            mock_instance = MagicMock()
            mock_instance.send_make_command.side_effect = Exception('Unexpected error')
            mock_tmetr_service.return_value = mock_instance
            
            # Send webhook request
            response = client.post(
                '/v1/yook-pay-webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json'
            )
        
        # Assert response is 200 (not 503)
        self.assertEqual(response.status_code, 200)
        
        # Retrieve order and check status
        order = Order.objects.get(id='test-order-webhook')
        self.assertEqual(order.status, 'make_failed')
    
    @pytest.mark.timeout(30)
    def test_webhook_success_sets_make_pending(self):
        """Test that successful send_make_command sets status to make_pending."""
        from unittest.mock import patch, MagicMock
        from django.test import Client
        import json
        
        client = Client()
        
        # Reset order status to paid
        self.order.status = 'paid'
        self.order.save()
        
        # Prepare webhook payload
        webhook_payload = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'payment-789',
                'amount': {'value': '180.00'},
                'metadata': {
                    'order_uuid': 'test-order-webhook',
                    'drink_number': 'drink-002',
                    'size': '1'
                }
            }
        }
        
        # Mock TmetrService.send_make_command to succeed
        with patch('payments.views.TmetrService') as mock_tmetr_service:
            mock_instance = MagicMock()
            mock_instance.send_make_command.return_value = {'status': 'success'}
            mock_tmetr_service.return_value = mock_instance
            
            # Send webhook request
            response = client.post(
                '/v1/yook-pay-webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json'
            )
        
        # Assert response is 200
        self.assertEqual(response.status_code, 200)
        
        # Retrieve order and check status is make_pending (not make_failed)
        order = Order.objects.get(id='test-order-webhook')
        self.assertEqual(order.status, 'make_pending')
