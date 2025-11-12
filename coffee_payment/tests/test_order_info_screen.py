"""
Unit tests for order info screen functionality.
Tests the show_order_info, initiate_payment views and payment flow routing.
"""
import json
import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from django.utils.timezone import now
from django.http import HttpResponseRedirect, JsonResponse
from payments.models import Merchant, Device, Order, MerchantCredentials
from payments.views import show_order_info, initiate_payment, yookassa_payment_process
from payments.user_messages import ERROR_MESSAGES


class OrderInfoScreenTestCase(TestCase):
    """Base test case with fixtures and helper functions for order info screen tests."""
    
    def setUp(self):
        """Set up test fixtures for Device, Merchant, Order with required fields."""
        self.factory = RequestFactory()
        
        # Create test merchant
        self.merchant = Merchant.objects.create(
            name='Test Coffee Shop',
            contact_email='test@example.com',
            bank_account='1234567890',
            valid_until=(now() + timedelta(days=365)).date()
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
        
        # Create test device without logo_url and client_info
        self.device_no_extras = Device.objects.create(
            device_uuid='test-device-no-extras',
            merchant=self.merchant,
            location='Test Location No Extras',
            status='online',
            last_interaction=now(),
            payment_scenario='Yookassa',
            logo_url=None,
            client_info=None
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
    
    def create_test_order(self, device, size=2, price=5000, status='created'):
        """
        Helper function to create a test order.
        
        Args:
            device: Device instance
            size: Drink size (1=Small, 2=Medium, 3=Large)
            price: Price in kopecks
            status: Order status
            
        Returns:
            Order instance
        """
        order = Order.objects.create(
            drink_name='Test Cappuccino',
            device=device,
            merchant=self.merchant,
            size=size,
            price=price,
            status=status
        )
        return order
    
    def create_expired_order(self, device):
        """
        Helper function to create an expired order.
        
        Args:
            device: Device instance
            
        Returns:
            Order instance with expired timestamp
        """
        order = Order.objects.create(
            drink_name='Expired Latte',
            device=device,
            merchant=self.merchant,
            size=2,
            price=6000,
            status='created',
            expires_at=now() - timedelta(minutes=1)  # Expired 1 minute ago
        )
        return order
    
    def create_drink_details(self, name='Test Cappuccino', price=5000, drink_id='test-drink-123'):
        """
        Helper function to create drink details dictionary.
        
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


class ShowOrderInfoTests(OrderInfoScreenTestCase):
    """Tests for show_order_info function."""
    
    def test_show_order_info_yookassa_scenario_with_all_context_data(self):
        """Test order info screen renders for Yookassa scenario with all context data."""
        order = self.create_test_order(self.device_yookassa, size=2, price=5000)
        drink_details = self.create_drink_details(name='Cappuccino', price=5000)
        
        request = self.factory.get('/test')
        response = show_order_info(request, self.device_yookassa, order, drink_details)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cappuccino', response.content)
        self.assertIn(b'Test Location Yookassa', response.content)
        self.assertIn(b'50.0', response.content)  # Price in rubles
        self.assertIn(b'https://example.com/logo.png', response.content)
        self.assertIn(b'Test client information', response.content)
    
    def test_show_order_info_tbank_scenario_with_all_context_data(self):
        """Test order info screen renders for TBank scenario with all context data."""
        order = self.create_test_order(self.device_tbank, size=3, price=7500)
        drink_details = self.create_drink_details(name='Latte', price=7500)
        
        request = self.factory.get('/test')
        response = show_order_info(request, self.device_tbank, order, drink_details)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Latte', response.content)
        self.assertIn(b'Test Location TBank', response.content)
        self.assertIn(b'75.0', response.content)  # Price in rubles
        self.assertIn(b'https://example.com/logo-tbank.png', response.content)
        self.assertIn(b'TBank client info', response.content)
    
    def test_drink_size_mapping_small(self):
        """Test drink size mapping: 1 → маленький."""
        order = self.create_test_order(self.device_yookassa, size=1)
        drink_details = self.create_drink_details()
        
        request = self.factory.get('/test')
        response = show_order_info(request, self.device_yookassa, order, drink_details)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('маленький'.encode('utf-8'), response.content)
    
    def test_drink_size_mapping_medium(self):
        """Test drink size mapping: 2 → средний."""
        order = self.create_test_order(self.device_yookassa, size=2)
        drink_details = self.create_drink_details()
        
        request = self.factory.get('/test')
        response = show_order_info(request, self.device_yookassa, order, drink_details)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('средний'.encode('utf-8'), response.content)
    
    def test_drink_size_mapping_large(self):
        """Test drink size mapping: 3 → большой."""
        order = self.create_test_order(self.device_yookassa, size=3)
        drink_details = self.create_drink_details()
        
        request = self.factory.get('/test')
        response = show_order_info(request, self.device_yookassa, order, drink_details)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('большой'.encode('utf-8'), response.content)
    
    def test_price_formatting_from_kopecks_to_rubles(self):
        """Test price formatting from kopecks to rubles."""
        order = self.create_test_order(self.device_yookassa, price=12345)
        drink_details = self.create_drink_details(price=12345)
        
        request = self.factory.get('/test')
        response = show_order_info(request, self.device_yookassa, order, drink_details)
        
        self.assertEqual(response.status_code, 200)
        # Price should be formatted as 123.45 rubles
        self.assertIn(b'123.45', response.content)
    
    def test_screen_renders_correctly_when_logo_url_is_none(self):
        """Test screen renders correctly when logo_url is None."""
        order = self.create_test_order(self.device_no_extras)
        drink_details = self.create_drink_details()
        
        request = self.factory.get('/test')
        response = show_order_info(request, self.device_no_extras, order, drink_details)
        
        self.assertEqual(response.status_code, 200)
        # Should not contain logo image tag when logo_url is None
        self.assertNotIn(b'<img', response.content)
    
    def test_screen_renders_correctly_when_client_info_is_none(self):
        """Test screen renders correctly when client_info is None."""
        order = self.create_test_order(self.device_no_extras)
        drink_details = self.create_drink_details()
        
        request = self.factory.get('/test')
        response = show_order_info(request, self.device_no_extras, order, drink_details)
        
        self.assertEqual(response.status_code, 200)
        # The CSS class 'client-info' exists in the template, but the section should not be rendered
        # Check that the actual client info text is not present
        response_text = response.content.decode('utf-8')
        # Verify that there's no <div class="client-info"> with content
        self.assertNotIn('<div class="client-info">', response_text)


class InitiatePaymentTests(OrderInfoScreenTestCase):
    """Tests for initiate_payment function."""
    
    @patch('payments.services.payment_scenario_service.PaymentScenarioService.execute_scenario')
    def test_successful_payment_initiation_returns_redirect(self, mock_execute):
        """Test successful payment initiation returns redirect to payment URL."""
        order = self.create_test_order(self.device_yookassa)
        
        # Mock successful payment creation
        mock_response = HttpResponseRedirect('https://payment.example.com/pay')
        mock_execute.return_value = mock_response
        
        request = self.factory.post(
            '/v1/initiate-payment',
            data=json.dumps({'order_id': str(order.id)}),
            content_type='application/json'
        )
        
        response = initiate_payment(request)
        
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertEqual(response.url, 'https://payment.example.com/pay')
        mock_execute.assert_called_once()
    
    @patch('payments.services.yookassa_service.create_payment')
    def test_order_status_updates_to_pending_after_successful_payment(self, mock_create_payment):
        """Test order status updates to 'pending' after successful payment creation."""
        order = self.create_test_order(self.device_yookassa)
        
        # Mock Yookassa payment creation
        mock_payment = MagicMock()
        mock_payment.json.return_value = json.dumps({
            'id': 'test-payment-id-123',
            'confirmation': {
                'confirmation_url': 'https://yookassa.example.com/pay'
            }
        })
        mock_create_payment.return_value = mock_payment
        
        request = self.factory.post(
            '/v1/initiate-payment',
            data=json.dumps({'order_id': str(order.id)}),
            content_type='application/json'
        )
        
        response = initiate_payment(request)
        
        # Refresh order from database
        order.refresh_from_db()
        
        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.external_order_id, 'test-payment-id-123')
    
    def test_expired_order_returns_400_with_error_message(self):
        """Test expired order returns 400 response with appropriate error message."""
        order = self.create_expired_order(self.device_yookassa)
        
        request = self.factory.post(
            '/v1/initiate-payment',
            data=json.dumps({'order_id': str(order.id)}),
            content_type='application/json'
        )
        
        response = initiate_payment(request)
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], ERROR_MESSAGES['order_expired'])
    
    def test_missing_order_id_parameter_returns_400(self):
        """Test missing order_id parameter returns 400 response."""
        request = self.factory.post(
            '/v1/initiate-payment',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        response = initiate_payment(request)
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], ERROR_MESSAGES['missing_order_id'])
    
    def test_non_existent_order_id_returns_404(self):
        """Test non-existent order_id returns 404 response."""
        fake_order_id = str(uuid.uuid4())
        
        request = self.factory.post(
            '/v1/initiate-payment',
            data=json.dumps({'order_id': fake_order_id}),
            content_type='application/json'
        )
        
        response = initiate_payment(request)
        
        self.assertEqual(response.status_code, 404)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], ERROR_MESSAGES['order_not_found'])
    
    @patch('payments.services.payment_scenario_service.PaymentScenarioService.execute_scenario')
    def test_payment_creation_failure_returns_503_with_user_friendly_message(self, mock_execute):
        """Test payment creation failure returns 503 response with user-friendly message."""
        order = self.create_test_order(self.device_yookassa)
        
        # Mock payment creation failure
        mock_execute.side_effect = Exception('Payment provider API error')
        
        request = self.factory.post(
            '/v1/initiate-payment',
            data=json.dumps({'order_id': str(order.id)}),
            content_type='application/json'
        )
        
        response = initiate_payment(request)
        
        self.assertEqual(response.status_code, 503)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], ERROR_MESSAGES['payment_creation_failed'])


class PaymentFlowRoutingTests(OrderInfoScreenTestCase):
    """Tests for payment flow routing based on payment scenario."""
    
    @patch('payments.services.tmetr_service.TmetrService.send_static_drink')
    def test_custom_scenario_bypasses_order_info_screen(self, mock_send_static_drink):
        """Test Custom scenario bypasses order info screen and redirects directly."""
        # Mock Tmetr API response
        mock_send_static_drink.return_value = {
            'name': 'Espresso',
            'price': 4000,
            'drink_id': 'espresso-123'
        }
        
        request = self.factory.get(
            '/v1/yook-pay',
            {
                'deviceUuid': 'test-device-custom',
                'drinkName': 'Espresso',
                'drinkNo': 'espresso-123',
                'uuid': str(uuid.uuid4()),
                'size': '1'
            }
        )
        
        response = yookassa_payment_process(request)
        
        # Should redirect directly to custom URL without showing order info screen
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertIn('custom-payment.example.com', response.url)
        self.assertIn('order_id=', response.url)
        self.assertIn('drink_name=', response.url)
    
    @patch('payments.services.tmetr_service.TmetrService.send_static_drink')
    def test_yookassa_scenario_shows_order_info_screen(self, mock_send_static_drink):
        """Test Yookassa scenario shows order info screen instead of immediate redirect."""
        # Mock Tmetr API response
        mock_send_static_drink.return_value = {
            'name': 'Americano',
            'price': 4500,
            'drink_id': 'americano-456'
        }
        
        request = self.factory.get(
            '/v1/yook-pay',
            {
                'deviceUuid': 'test-device-yookassa',
                'drinkName': 'Americano',
                'drinkNo': 'americano-456',
                'uuid': str(uuid.uuid4()),
                'size': '0'
            }
        )
        
        response = yookassa_payment_process(request)
        
        # Should render order info screen, not redirect
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Americano', response.content)
        self.assertIn(b'Test Location Yookassa', response.content)
        # Should contain payment button
        self.assertIn('initiatePayment'.encode('utf-8'), response.content)
    
    @patch('payments.services.tmetr_service.TmetrService.send_static_drink')
    def test_tbank_scenario_shows_order_info_screen(self, mock_send_static_drink):
        """Test TBank scenario shows order info screen instead of immediate redirect."""
        # Mock Tmetr API response
        mock_send_static_drink.return_value = {
            'name': 'Flat White',
            'price': 5500,
            'drink_id': 'flatwhite-789'
        }
        
        request = self.factory.get(
            '/v1/yook-pay',
            {
                'deviceUuid': 'test-device-tbank',
                'drinkName': 'Flat White',
                'drinkNo': 'flatwhite-789',
                'uuid': str(uuid.uuid4()),
                'size': '2'
            }
        )
        
        response = yookassa_payment_process(request)
        
        # Should render order info screen, not redirect
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Flat White', response.content)
        self.assertIn(b'Test Location TBank', response.content)
        # Should contain payment button
        self.assertIn('initiatePayment'.encode('utf-8'), response.content)
