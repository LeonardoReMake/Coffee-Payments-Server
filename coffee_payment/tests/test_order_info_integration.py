"""
Integration tests for complete payment flow with order info screen.
Tests end-to-end flows from QR code scan to payment initiation.
"""
import json
import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.utils.timezone import now
from payments.models import Merchant, Device, Order, MerchantCredentials


class OrderInfoIntegrationTestCase(TestCase):
    """Base test case with fixtures for integration testing."""
    
    def setUp(self):
        """Set up test client and fixtures for end-to-end testing."""
        self.client = Client()
        
        # Create test merchant
        self.merchant = Merchant.objects.create(
            name='Integration Test Coffee Shop',
            contact_email='integration@example.com',
            bank_account='9876543210',
            valid_until=(now() + timedelta(days=365)).date()
        )
        
        # Create test device with Yookassa scenario
        self.device_yookassa = Device.objects.create(
            device_uuid='integration-device-yookassa',
            merchant=self.merchant,
            location='Integration Test Location Yookassa',
            status='online',
            last_interaction=now(),
            payment_scenario='Yookassa',
            logo_url='https://example.com/integration-logo.png',
            client_info='Integration test client information'
        )
        
        # Create test device with TBank scenario
        self.device_tbank = Device.objects.create(
            device_uuid='integration-device-tbank',
            merchant=self.merchant,
            location='Integration Test Location TBank',
            status='online',
            last_interaction=now(),
            payment_scenario='TBank',
            logo_url='https://example.com/tbank-logo.png',
            client_info='TBank integration test info'
        )
        
        # Create test device with Custom scenario
        self.device_custom = Device.objects.create(
            device_uuid='integration-device-custom',
            merchant=self.merchant,
            location='Integration Test Location Custom',
            status='online',
            last_interaction=now(),
            payment_scenario='Custom',
            redirect_url='https://custom-integration.example.com/pay'
        )
        
        # Create merchant credentials for Yookassa
        self.yookassa_credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={
                'account_id': 'integration_account_id',
                'secret_key': 'integration_secret_key'
            }
        )
        
        # Create merchant credentials for TBank
        self.tbank_credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='TBank',
            credentials={
                'terminal_key': 'integration_terminal_key',
                'secret_key': 'integration_tbank_secret'
            }
        )


class FullYookassaPaymentFlowTest(OrderInfoIntegrationTestCase):
    """Test full Yookassa payment flow from QR scan to payment initiation."""
    
    @patch('payments.services.tmetr_service.TmetrService.send_static_drink')
    def test_full_yookassa_payment_flow(self, mock_send_static_drink):
        """
        Test complete Yookassa payment flow:
        1. Simulate QR code scan to yookassa_payment_process endpoint
        2. Verify order info screen is rendered with correct data
        3. Simulate payment button click to initiate_payment endpoint
        4. Verify redirect to Yookassa payment URL
        5. Verify order status transitions: created → pending
        """
        # Mock Tmetr API response for drink price
        mock_send_static_drink.return_value = {
            'name': 'Integration Americano',
            'price': 4500,  # 45 rubles in kopecks
            'drink_id': 'integration-americano-123'
        }
        
        # Step 1: Simulate QR code scan to yookassa_payment_process endpoint
        qr_params = {
            'deviceUuid': 'integration-device-yookassa',
            'drinkName': 'Americano',
            'drinkNo': 'integration-americano-123',
            'uuid': str(uuid.uuid4()),
            'size': '1'  # Medium size (0-indexed in URL)
        }
        
        response = self.client.get('/v1/yook-pay', qr_params)
        
        # Step 2: Verify order info screen is rendered with correct data
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Integration Americano', response.content)
        self.assertIn(b'Integration Test Location Yookassa', response.content)
        self.assertIn(b'45.0', response.content)  # Price in rubles
        self.assertIn(b'https://example.com/integration-logo.png', response.content)
        self.assertIn(b'Integration test client information', response.content)
        self.assertIn('средний'.encode('utf-8'), response.content)  # Size mapping
        
        # Verify order was created with 'created' status
        order = Order.objects.filter(
            device=self.device_yookassa,
            drink_name='Americano'
        ).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'created')
        self.assertEqual(order.size, 2)  # Medium = 2 in database
        self.assertEqual(order.price, 4500)
        
        # Step 3: Simulate payment button click to initiate_payment endpoint
        with patch('payments.services.yookassa_service.create_payment') as mock_create_payment:
            # Mock Yookassa payment creation
            mock_payment = MagicMock()
            mock_payment.json.return_value = json.dumps({
                'id': 'integration-payment-id-456',
                'confirmation': {
                    'confirmation_url': 'https://yookassa.integration.example.com/pay'
                }
            })
            mock_create_payment.return_value = mock_payment
            
            payment_response = self.client.post(
                '/v1/initiate-payment',
                data=json.dumps({'order_id': str(order.id)}),
                content_type='application/json'
            )
            
            # Step 4: Verify JSON response with redirect URL to Yookassa payment
            self.assertEqual(payment_response.status_code, 200)
            payment_data = json.loads(payment_response.content)
            self.assertEqual(
                payment_data['redirect_url'],
                'https://yookassa.integration.example.com/pay'
            )
            
            # Step 5: Verify order status transitions: created → pending
            order.refresh_from_db()
            self.assertEqual(order.status, 'pending')
            self.assertEqual(order.payment_reference_id, 'integration-payment-id-456')
        
        # Verify Tmetr API was called with correct parameters
        mock_send_static_drink.assert_called_once_with(
            device_id='integration-device-yookassa',
            drink_id_at_device='integration-americano-123',
            drink_size='MEDIUM'
        )
