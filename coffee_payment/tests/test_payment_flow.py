"""
Unit tests for process_payment_flow functionality.
Tests the main payment flow handler for QR code scans from coffee machines.
"""
import json
import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from django.utils.timezone import now
from django.http import HttpResponseRedirect, JsonResponse
from payments.models import Merchant, Device, Order, MerchantCredentials
from payments.views import process_payment_flow
from payments.user_messages import ERROR_MESSAGES


class ProcessPaymentFlowTestCase(TestCase):
    """Base test case with fixtures and helper functions for process_payment_flow tests."""
    
    def setUp(self):
        """Set up test fixtures for Device, Merchant, MerchantCredentials."""
        self.factory = RequestFactory()
        
        # Create test merchant
        self.merchant = Merchant.objects.create(
            name='Test Coffee Shop',
            contact_email='test@example.com',
            bank_account='1234567890',
            valid_until=(now() + timedelta(days=365)).date()
        )
        
        # Create expired merchant for testing
        self.expired_merchant = Merchant.objects.create(
            name='Expired Coffee Shop',
            contact_email='expired@example.com',
            bank_account='0987654321',
            valid_until=(now() - timedelta(days=1)).date()
        )
        
        # Create test device with Yookassa scenario
        self.device_yookassa = Device.objects.create(
            device_uuid='test-device-yookassa',
            merchant=self.merchant,
            location='Test Location Yookassa',
            status='online',
            last_interaction=now(),
            payment_scenario='Yookassa',
            logo_url='https://example.com/logo.png',
            client_info='Test client information'
        )
        
        # Create test device with TBank scenario
        self.device_tbank = Device.objects.create(
            device_uuid='test-device-tbank',
            merchant=self.merchant,
            location='Test Location TBank',
            status='online',
            last_interaction=now(),
            payment_scenario='TBank',
            logo_url='https://example.com/logo-tbank.png',
            client_info='TBank client info'
        )
        
        # Create test device with Custom scenario
        self.device_custom = Device.objects.create(
            device_uuid='test-device-custom',
            merchant=self.merchant,
            location='Test Location Custom',
            status='online',
            last_interaction=now(),
            payment_scenario='Custom',
            redirect_url='https://custom-payment.example.com/pay'
        )
        
        # Create test device with expired merchant
        self.device_expired_merchant = Device.objects.create(
            device_uuid='test-device-expired',
            merchant=self.expired_merchant,
            location='Test Location Expired',
            status='online',
            last_interaction=now(),
            payment_scenario='Yookassa'
        )
        
        # Create merchant credentials for Yookassa
        self.yookassa_credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={
                'account_id': 'test_account_id',
                'secret_key': 'test_secret_key'
            }
        )
        
        # Create merchant credentials for TBank
        self.tbank_credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='TBank',
            credentials={
                'terminal_key': 'test_terminal_key',
                'secret_key': 'test_tbank_secret'
            }
        )
    
    def create_mock_tmetr_response(self, name='Test Cappuccino', price=5000, drink_id='test-drink-123'):
        """
        Helper function to create mock Tmetr API response.
        
        Args:
            name: Drink name
            price: Price in kopecks
            drink_id: Drink identifier
            
        Returns:
            Dict with drink details
        """
        return {
            'name': name,
            'price': price,
            'drink_id': drink_id
        }


class SuccessfulScenariosTests(ProcessPaymentFlowTestCase):
    """Tests for successful payment flow scenarios."""
    
    @patch('payments.services.tmetr_service.TmetrService.send_static_drink')
    def test_process_payment_flow_yookassa_success(self, mock_send_static_drink):
        """Test successful Yookassa scenario: creates Order and displays order info screen."""
        # Mock Tmetr API response
        mock_send_static_drink.return_value = self.create_mock_tmetr_response(
            name='Cappuccino',
            price=5000
        )
        
        # Create request with all required parameters
        request = self.factory.get(
            '/v1/pay',
            {
                'deviceUuid': 'test-device-yookassa',
                'drinkName': 'Cappuccino',
                'drinkNo': 'cappuccino-123',
                'uuid': str(uuid.uuid4()),
                'size': '1'  # Medium
            }
        )
        
        response = process_payment_flow(request)
        
        # Verify response is successful and renders order info screen
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cappuccino', response.content)
        self.assertIn(b'Test Location Yookassa', response.content)
        self.assertIn(b'50.0', response.content)  # Price in rubles
        
        # Verify Order was created with correct status
        order = Order.objects.filter(
            device=self.device_yookassa,
            drink_name='Cappuccino'
        ).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'created')
        self.assertEqual(order.size, 2)  # Medium = 2 in database
        self.assertEqual(order.price, 5000)
        
        # Verify Tmetr API was called with correct parameters
        mock_send_static_drink.assert_called_once_with(
            device_id='test-device-yookassa',
            drink_id_at_device='cappuccino-123',
            drink_size='MEDIUM'
        )
    
    @patch('payments.services.tmetr_service.TmetrService.send_static_drink')
    def test_process_payment_flow_tbank_success(self, mock_send_static_drink):
        """Test successful TBank scenario: creates Order and displays order info screen."""
        # Mock Tmetr API response
        mock_send_static_drink.return_value = self.create_mock_tmetr_response(
            name='Latte',
            price=7500
        )
        
        # Create request with all required parameters
        request = self.factory.get(
            '/v1/pay',
            {
                'deviceUuid': 'test-device-tbank',
                'drinkName': 'Latte',
                'drinkNo': 'latte-456',
                'uuid': str(uuid.uuid4()),
                'size': '2'  # Large
            }
        )
        
        response = process_payment_flow(request)
        
        # Verify response is successful and renders order info screen
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Latte', response.content)
        self.assertIn(b'Test Location TBank', response.content)
        self.assertIn(b'75.0', response.content)  # Price in rubles
        
        # Verify Order was created with correct status
        order = Order.objects.filter(
            device=self.device_tbank,
            drink_name='Latte'
        ).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'created')
        self.assertEqual(order.size, 3)  # Large = 3 in database
        self.assertEqual(order.price, 7500)
    
    @patch('payments.services.payment_scenario_service.PaymentScenarioService.execute_scenario')
    @patch('payments.services.tmetr_service.TmetrService.send_static_drink')
    def test_process_payment_flow_custom_success(self, mock_send_static_drink, mock_execute_scenario):
        """Test successful Custom scenario: creates Order and redirects directly."""
        # Mock Tmetr API response
        mock_send_static_drink.return_value = self.create_mock_tmetr_response(
            name='Espresso',
            price=4000
        )
        
        # Mock PaymentScenarioService to return redirect
        mock_execute_scenario.return_value = HttpResponseRedirect(
            'https://custom-payment.example.com/pay?order_id=test-order-123'
        )
        
        # Create request with all required parameters
        request = self.factory.get(
            '/v1/pay',
            {
                'deviceUuid': 'test-device-custom',
                'drinkName': 'Espresso',
                'drinkNo': 'espresso-789',
                'uuid': str(uuid.uuid4()),
                'size': '0'  # Small
            }
        )
        
        response = process_payment_flow(request)
        
        # Verify response is a redirect (not order info screen)
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertIn('custom-payment.example.com', response.url)
        
        # Verify Order was created with correct status
        order = Order.objects.filter(
            device=self.device_custom,
            drink_name='Espresso'
        ).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'created')
        self.assertEqual(order.size, 1)  # Small = 1 in database
        self.assertEqual(order.price, 4000)
        
        # Verify PaymentScenarioService was called
        mock_execute_scenario.assert_called_once()


class ErrorHandlingTests(ProcessPaymentFlowTestCase):
    """Tests for error handling in process_payment_flow."""
    
    def test_process_payment_flow_missing_parameters(self):
        """Test HTTP 400 when required parameters are missing."""
        # Test missing deviceUuid
        request = self.factory.get(
            '/v1/pay',
            {
                'drinkName': 'Cappuccino',
                'drinkNo': 'cappuccino-123',
                'uuid': str(uuid.uuid4()),
                'size': '1'
            }
        )
        
        response = process_payment_flow(request)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn(ERROR_MESSAGES['missing_parameters'].encode('utf-8'), response.content)
    
    def test_process_payment_flow_device_not_found(self):
        """Test HTTP 404 when device does not exist."""
        request = self.factory.get(
            '/v1/pay',
            {
                'deviceUuid': 'non-existent-device',
                'drinkName': 'Cappuccino',
                'drinkNo': 'cappuccino-123',
                'uuid': str(uuid.uuid4()),
                'size': '1'
            }
        )
        
        response = process_payment_flow(request)
        
        self.assertEqual(response.status_code, 404)
        self.assertIn(ERROR_MESSAGES['device_not_found'].encode('utf-8'), response.content)
    
    def test_process_payment_flow_merchant_expired(self):
        """Test HTTP 403 when merchant permissions have expired."""
        request = self.factory.get(
            '/v1/pay',
            {
                'deviceUuid': 'test-device-expired',
                'drinkName': 'Cappuccino',
                'drinkNo': 'cappuccino-123',
                'uuid': str(uuid.uuid4()),
                'size': '1'
            }
        )
        
        response = process_payment_flow(request)
        
        self.assertEqual(response.status_code, 403)
        self.assertIn(ERROR_MESSAGES['merchant_expired'].encode('utf-8'), response.content)
    
    @patch('payments.services.tmetr_service.TmetrService.send_static_drink')
    def test_process_payment_flow_tmetr_api_failure(self, mock_send_static_drink):
        """Test HTTP 503 when Tmetr API request fails."""
        # Mock Tmetr API to raise RequestException
        import requests
        mock_send_static_drink.side_effect = requests.RequestException('Tmetr API connection error')
        
        request = self.factory.get(
            '/v1/pay',
            {
                'deviceUuid': 'test-device-yookassa',
                'drinkName': 'Cappuccino',
                'drinkNo': 'cappuccino-123',
                'uuid': str(uuid.uuid4()),
                'size': '1'
            }
        )
        
        response = process_payment_flow(request)
        
        self.assertEqual(response.status_code, 503)
        self.assertIn(ERROR_MESSAGES['service_unavailable'].encode('utf-8'), response.content)
    
    @patch('payments.services.payment_scenario_service.PaymentScenarioService.execute_scenario')
    @patch('payments.services.tmetr_service.TmetrService.send_static_drink')
    def test_process_payment_flow_missing_credentials(self, mock_send_static_drink, mock_execute_scenario):
        """Test HTTP 503 when payment credentials are missing for Custom scenario."""
        # Mock Tmetr API response
        mock_send_static_drink.return_value = self.create_mock_tmetr_response()
        
        # Mock PaymentScenarioService to raise ValueError (missing credentials)
        mock_execute_scenario.side_effect = ValueError('Missing redirect_url for Custom scenario')
        
        request = self.factory.get(
            '/v1/pay',
            {
                'deviceUuid': 'test-device-custom',
                'drinkName': 'Espresso',
                'drinkNo': 'espresso-789',
                'uuid': str(uuid.uuid4()),
                'size': '0'
            }
        )
        
        response = process_payment_flow(request)
        
        self.assertEqual(response.status_code, 503)
        self.assertIn(ERROR_MESSAGES['missing_credentials'].encode('utf-8'), response.content)
        
        # Verify order status was set to 'failed'
        order = Order.objects.filter(
            device=self.device_custom,
            drink_name='Espresso'
        ).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'failed')
