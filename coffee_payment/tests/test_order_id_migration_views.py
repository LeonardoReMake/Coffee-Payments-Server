"""
Tests for Order ID migration - views layer changes.
Tests that views correctly handle machine-generated string IDs.
"""
from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
from payments.models import Device, Merchant, Order
from unittest.mock import patch, MagicMock
import json


class OrderIDMigrationViewsTests(TestCase):
    """Test views with machine-generated order IDs."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        
        # Create test merchant
        self.merchant = Merchant.objects.create(
            name='Test Merchant',
            contact_email='test@example.com',
            bank_account='1234567890',
            valid_until=(timezone.now() + timedelta(days=30)).date()
        )
        
        # Create test device
        self.device = Device.objects.create(
            device_uuid='test-device-123',
            merchant=self.merchant,
            payment_scenario='Yookassa',
            location='Test Location',
            status='online',
            last_interaction=timezone.now()
        )
    
    def test_order_creation_with_machine_generated_id(self):
        """Test that orders are created with machine-generated IDs from QR parameters."""
        machine_id = '20250317110122659ba6d7-9ace-cndn'
        
        with patch('payments.services.validation_service.OrderValidationService.execute_validation_chain') as mock_validation, \
             patch('payments.services.tmetr_service.TmetrService.send_static_drink') as mock_tmetr:
            
            # Mock validation chain to allow order creation
            mock_validation.return_value = {
                'valid': True,
                'should_create_new_order': True,
                'error_message': None,
                'existing_order': None
            }
            
            # Mock Tmetr API response
            mock_tmetr.return_value = {
                'price': 15000,
                'name': 'Americano',
                'drink_id': 'drink123'
            }
            
            # Make request with machine-generated ID
            response = self.client.get('/v1/pay', {
                'deviceUuid': 'test-device-123',
                'drinkName': 'Americano',
                'drinkNo': 'drink123',
                'uuid': machine_id,
                'size': '1'
            })
            
            # Verify order was created with machine ID
            order = Order.objects.get(id=machine_id)
            self.assertEqual(order.id, machine_id)
            self.assertEqual(order.drink_name, 'Americano')
            self.assertEqual(order.status, 'created')
    
    def test_empty_order_id_validation(self):
        """Test that empty order IDs are rejected."""
        response = self.client.get('/v1/pay', {
            'deviceUuid': 'test-device-123',
            'drinkName': 'Americano',
            'drinkNo': 'drink123',
            'uuid': '   ',  # Empty/whitespace only
            'size': '1'
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Некорректный идентификатор заказа', response.content.decode())
    
    def test_long_order_id_validation(self):
        """Test that order IDs exceeding 255 characters are rejected."""
        long_id = 'x' * 256
        
        response = self.client.get('/v1/pay', {
            'deviceUuid': 'test-device-123',
            'drinkName': 'Americano',
            'drinkNo': 'drink123',
            'uuid': long_id,
            'size': '1'
        })
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Некорректный идентификатор заказа', response.content.decode())
    
    def test_webhook_lookup_by_machine_id(self):
        """Test that webhook looks up orders by machine-generated ID."""
        machine_id = '20250317110122659ba6d7-9ace-cndn'
        
        # Create order with machine-generated ID
        order = Order.objects.create(
            id=machine_id,
            drink_name='Americano',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=15000,
            status='created',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Simulate webhook payload
        webhook_payload = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'payment_12345',
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
        
        with patch('payments.services.tmetr_service.TmetrService.send_make_command') as mock_make:
            mock_make.return_value = None
            
            response = self.client.post(
                '/v1/yookassa/webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            
            # Verify order was found and updated
            order.refresh_from_db()
            self.assertEqual(order.status, 'make_pending')
            self.assertEqual(order.payment_reference_id, 'payment_12345')
    
    def test_webhook_stores_payment_reference_id(self):
        """Test that webhook stores payment system ID in payment_reference_id field."""
        machine_id = 'test-order-456'
        payment_id = 'yookassa_payment_789'
        
        # Create order
        order = Order.objects.create(
            id=machine_id,
            drink_name='Latte',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=18000,
            status='created',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Simulate webhook
        webhook_payload = {
            'event': 'payment.succeeded',
            'object': {
                'id': payment_id,
                'metadata': {
                    'order_uuid': machine_id,
                    'drink_number': 'drink456',
                    'size': '1'
                },
                'amount': {
                    'value': '180.00'
                }
            }
        }
        
        with patch('payments.services.tmetr_service.TmetrService.send_make_command'):
            self.client.post(
                '/v1/yookassa/webhook',
                data=json.dumps(webhook_payload),
                content_type='application/json'
            )
        
        # Verify payment_reference_id was stored
        order.refresh_from_db()
        self.assertEqual(order.payment_reference_id, payment_id)
    
    def test_initiate_payment_with_string_order_id(self):
        """Test that initiate_payment works with string-based order IDs."""
        machine_id = 'machine-order-789'
        
        # Create order
        order = Order.objects.create(
            id=machine_id,
            drink_name='Cappuccino',
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=16000,
            status='created',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        with patch('payments.services.payment_scenario_service.PaymentScenarioService.execute_scenario') as mock_execute:
            from django.http import HttpResponseRedirect
            mock_execute.return_value = HttpResponseRedirect('https://payment.example.com')
            
            response = self.client.post(
                '/v1/initiate-payment',
                data=json.dumps({'order_id': machine_id}),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            response_data = json.loads(response.content)
            self.assertIn('redirect_url', response_data)
            self.assertEqual(response_data['redirect_url'], 'https://payment.example.com')
