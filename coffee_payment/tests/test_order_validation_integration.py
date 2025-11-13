"""
Integration tests for complete validation flow in process_payment_flow.
Tests validation chain integration with views and error page rendering.
"""
import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, override_settings
from django.utils.timezone import now
from django.urls import reverse
from payments.models import Merchant, Device, Order
from payments.user_messages import ERROR_MESSAGES


class ValidationFlowIntegrationTestCase(TestCase):
    """Base test case with fixtures for validation flow integration tests."""
    
    def setUp(self):
        """Set up test fixtures for integration tests."""
        # Create test merchant
        self.merchant = Merchant.objects.create(
            name='Test Coffee Shop',
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
            payment_scenario='Yookassa'
        )
        
        # Initialize test client
        self.client = Client()
        
        # Test parameters
        self.order_uuid = str(uuid.uuid4())
        self.device_uuid = 'test-device-uuid'
        self.drink_name = 'Cappuccino'
        self.drink_number = 'drink-123'
        self.drink_size = '1'


class CompleteValidationFlowTests(ValidationFlowIntegrationTestCase):
    """Tests for complete flow with all validations passing."""
    
    @patch('payments.views.TmetrService')
    @patch('payments.services.validation_service.TmetrService')
    @override_settings(DEVICE_ONLINE_THRESHOLD_MINUTES=5)
    def test_complete_flow_all_validations_pass(self, mock_validation_tmetr_class, mock_views_tmetr_class):
        """Test complete flow with all validations passing creates order and shows order info screen."""
        # Mock Tmetr heartbeat API for validation
        mock_validation_tmetr = MagicMock()
        mock_validation_tmetr_class.return_value = mock_validation_tmetr
        
        recent_heartbeat = int((now() - timedelta(minutes=2)).timestamp())
        mock_validation_tmetr.get_device_heartbeat.return_value = {
            'content': [
                {
                    'deviceId': self.device_uuid,
                    'deviceIotName': 'test-device',
                    'heartbeatCreatedAt': recent_heartbeat
                }
            ],
            'totalElements': 1,
            'offset': 0,
            'limit': 1
        }
        
        # Mock Tmetr drink API for process_payment_flow
        mock_views_tmetr = MagicMock()
        mock_views_tmetr_class.return_value = mock_views_tmetr
        
        mock_views_tmetr.send_static_drink.return_value = {
            'price': 5000,
            'name': 'Cappuccino',
            'drink_id': 'drink-123'
        }
        
        # Make request to process_payment_flow
        response = self.client.get('/v1/pay', {
            'deviceUuid': self.device_uuid,
            'drinkName': self.drink_name,
            'drinkNo': self.drink_number,
            'size': self.drink_size,
            'uuid': self.order_uuid
        })
        
        # Verify response shows order info screen
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/order_info_screen.html')
        
        # Verify order was created (find by device and drink_name since UUID is auto-generated)
        order = Order.objects.filter(device=self.device, drink_name=self.drink_name).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.status, 'created')
        self.assertEqual(order.drink_name, self.drink_name)
        self.assertEqual(order.device, self.device)
        
        # Verify Tmetr APIs were called
        mock_validation_tmetr.get_device_heartbeat.assert_called_once_with(self.device_uuid)
        mock_views_tmetr.send_static_drink.assert_called_once()


class ValidationFailureTerminationTests(ValidationFlowIntegrationTestCase):
    """Tests for flow termination on each validation failure type."""
    
    @patch('payments.services.validation_service.OrderValidationService.validate_request_hash')
    def test_flow_termination_on_hash_validation_failure(self, mock_validate_hash):
        """Test flow terminates on hash validation failure and shows error page."""
        # Mock hash validation to fail
        mock_validate_hash.return_value = (False, ERROR_MESSAGES['invalid_request_hash'])
        
        # Make request
        response = self.client.get('/v1/pay', {
            'deviceUuid': self.device_uuid,
            'drinkName': self.drink_name,
            'drinkNo': self.drink_number,
            'size': self.drink_size,
            'uuid': self.order_uuid
        })
        
        # Verify error page is rendered
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'payments/error_page.html')
        self.assertIn(ERROR_MESSAGES['invalid_request_hash'], response.content.decode())
        
        # Verify no order was created
        self.assertFalse(Order.objects.filter(id=self.order_uuid).exists())
    
    @patch('payments.services.validation_service.TmetrService')
    @override_settings(DEVICE_ONLINE_THRESHOLD_MINUTES=5)
    def test_flow_termination_on_expired_order(self, mock_tmetr_service_class):
        """Test flow terminates when order exists but has expired."""
        # Create expired order
        Order.objects.create(
            id=self.order_uuid,
            device=self.device,
            merchant=self.merchant,
            drink_name=self.drink_name,
            size=2,
            price=5000,
            status='created',
            expires_at=now() - timedelta(minutes=5)
        )
        
        # Make request
        response = self.client.get('/v1/pay', {
            'deviceUuid': self.device_uuid,
            'drinkName': self.drink_name,
            'drinkNo': self.drink_number,
            'size': self.drink_size,
            'uuid': self.order_uuid
        })
        
        # Verify error page is rendered
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'payments/error_page.html')
        self.assertIn(ERROR_MESSAGES['order_expired'], response.content.decode())
    
    @patch('payments.services.validation_service.TmetrService')
    @override_settings(DEVICE_ONLINE_THRESHOLD_MINUTES=5)
    def test_flow_termination_on_device_offline(self, mock_tmetr_service_class):
        """Test flow terminates when device is offline."""
        # Mock Tmetr heartbeat API to return old heartbeat
        mock_tmetr_service = MagicMock()
        mock_tmetr_service_class.return_value = mock_tmetr_service
        
        old_heartbeat = int((now() - timedelta(minutes=10)).timestamp())
        mock_tmetr_service.get_device_heartbeat.return_value = {
            'content': [
                {
                    'deviceId': self.device_uuid,
                    'deviceIotName': 'test-device',
                    'heartbeatCreatedAt': old_heartbeat
                }
            ],
            'totalElements': 1,
            'offset': 0,
            'limit': 1
        }
        
        # Make request
        response = self.client.get('/v1/pay', {
            'deviceUuid': self.device_uuid,
            'drinkName': self.drink_name,
            'drinkNo': self.drink_number,
            'size': self.drink_size,
            'uuid': self.order_uuid
        })
        
        # Verify error page is rendered
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'payments/error_page.html')
        self.assertIn(ERROR_MESSAGES['device_offline'], response.content.decode())
        
        # Verify no order was created
        self.assertFalse(Order.objects.filter(id=self.order_uuid).exists())
    
    @patch('payments.services.validation_service.TmetrService')
    def test_flow_termination_on_heartbeat_check_failure(self, mock_tmetr_service_class):
        """Test flow terminates when heartbeat check fails due to API error."""
        # Mock Tmetr API to raise exception
        mock_tmetr_service = MagicMock()
        mock_tmetr_service_class.return_value = mock_tmetr_service
        
        import requests
        mock_tmetr_service.get_device_heartbeat.side_effect = requests.RequestException('API error')
        
        # Make request
        response = self.client.get('/v1/pay', {
            'deviceUuid': self.device_uuid,
            'drinkName': self.drink_name,
            'drinkNo': self.drink_number,
            'size': self.drink_size,
            'uuid': self.order_uuid
        })
        
        # Verify error page is rendered
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'payments/error_page.html')
        self.assertIn(ERROR_MESSAGES['heartbeat_check_failed'], response.content.decode())
        
        # Verify no order was created
        self.assertFalse(Order.objects.filter(id=self.order_uuid).exists())


class ExistingValidOrderScenarioTests(ValidationFlowIntegrationTestCase):
    """Tests for existing valid order scenario (no new order created)."""
    
    @patch('payments.views.TmetrService')
    @patch('payments.services.validation_service.TmetrService')
    @override_settings(DEVICE_ONLINE_THRESHOLD_MINUTES=5)
    def test_existing_valid_order_no_new_order_created(self, mock_validation_tmetr_class, mock_views_tmetr_class):
        """Test existing valid order scenario does not create new order."""
        # Create existing valid order
        existing_order = Order.objects.create(
            id=self.order_uuid,
            device=self.device,
            merchant=self.merchant,
            drink_name=self.drink_name,
            size=2,
            price=5000,
            status='created',
            expires_at=now() + timedelta(minutes=10)
        )
        
        # Mock Tmetr heartbeat API for validation
        mock_validation_tmetr = MagicMock()
        mock_validation_tmetr_class.return_value = mock_validation_tmetr
        
        recent_heartbeat = int((now() - timedelta(minutes=2)).timestamp())
        mock_validation_tmetr.get_device_heartbeat.return_value = {
            'content': [
                {
                    'deviceId': self.device_uuid,
                    'deviceIotName': 'test-device',
                    'heartbeatCreatedAt': recent_heartbeat
                }
            ],
            'totalElements': 1,
            'offset': 0,
            'limit': 1
        }
        
        # Mock Tmetr drink API for process_payment_flow
        mock_views_tmetr = MagicMock()
        mock_views_tmetr_class.return_value = mock_views_tmetr
        
        mock_views_tmetr.send_static_drink.return_value = {
            'price': 5000,
            'name': 'Cappuccino',
            'drink_id': 'drink-123'
        }
        
        # Get initial order count
        initial_order_count = Order.objects.count()
        
        # Make request
        response = self.client.get('/v1/pay', {
            'deviceUuid': self.device_uuid,
            'drinkName': self.drink_name,
            'drinkNo': self.drink_number,
            'size': self.drink_size,
            'uuid': self.order_uuid
        })
        
        # Verify response shows order info screen
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'payments/order_info_screen.html')
        
        # Verify no new order was created
        self.assertEqual(Order.objects.count(), initial_order_count)
        
        # Verify existing order is still in 'created' status
        existing_order.refresh_from_db()
        self.assertEqual(existing_order.status, 'created')
        
        # Verify the order in context is the existing order
        self.assertEqual(response.context['order'].id, existing_order.id)


class ErrorPageRenderingTests(ValidationFlowIntegrationTestCase):
    """Tests for error page rendering for each validation failure."""
    
    @patch('payments.services.validation_service.OrderValidationService.validate_request_hash')
    def test_error_page_rendering_for_hash_validation_failure(self, mock_validate_hash):
        """Test error page renders correctly for hash validation failure."""
        mock_validate_hash.return_value = (False, ERROR_MESSAGES['invalid_request_hash'])
        
        response = self.client.get('/v1/pay', {
            'deviceUuid': self.device_uuid,
            'drinkName': self.drink_name,
            'drinkNo': self.drink_number,
            'size': self.drink_size,
            'uuid': self.order_uuid
        })
        
        # Verify error page structure
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'payments/error_page.html')
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], ERROR_MESSAGES['invalid_request_hash'])
        self.assertEqual(response.context['status_code'], 400)
        
        # Verify user-friendly message is displayed
        content = response.content.decode()
        self.assertIn(ERROR_MESSAGES['invalid_request_hash'], content)
        # Verify no technical details are exposed
        self.assertNotIn('Exception', content)
        self.assertNotIn('Traceback', content)
    
    @patch('payments.services.validation_service.TmetrService')
    @override_settings(DEVICE_ONLINE_THRESHOLD_MINUTES=5)
    def test_error_page_rendering_for_order_expired(self, mock_tmetr_service_class):
        """Test error page renders correctly for expired order."""
        # Create expired order
        Order.objects.create(
            id=self.order_uuid,
            device=self.device,
            merchant=self.merchant,
            drink_name=self.drink_name,
            size=2,
            price=5000,
            status='created',
            expires_at=now() - timedelta(minutes=5)
        )
        
        response = self.client.get('/v1/pay', {
            'deviceUuid': self.device_uuid,
            'drinkName': self.drink_name,
            'drinkNo': self.drink_number,
            'size': self.drink_size,
            'uuid': self.order_uuid
        })
        
        # Verify error page structure
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'payments/error_page.html')
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], ERROR_MESSAGES['order_expired'])
        
        # Verify user-friendly message
        content = response.content.decode()
        self.assertIn(ERROR_MESSAGES['order_expired'], content)
    
    @patch('payments.services.validation_service.TmetrService')
    @override_settings(DEVICE_ONLINE_THRESHOLD_MINUTES=5)
    def test_error_page_rendering_for_device_offline(self, mock_tmetr_service_class):
        """Test error page renders correctly for device offline."""
        # Mock Tmetr heartbeat API to return old heartbeat
        mock_tmetr_service = MagicMock()
        mock_tmetr_service_class.return_value = mock_tmetr_service
        
        old_heartbeat = int((now() - timedelta(minutes=10)).timestamp())
        mock_tmetr_service.get_device_heartbeat.return_value = {
            'content': [
                {
                    'deviceId': self.device_uuid,
                    'deviceIotName': 'test-device',
                    'heartbeatCreatedAt': old_heartbeat
                }
            ],
            'totalElements': 1,
            'offset': 0,
            'limit': 1
        }
        
        response = self.client.get('/v1/pay', {
            'deviceUuid': self.device_uuid,
            'drinkName': self.drink_name,
            'drinkNo': self.drink_number,
            'size': self.drink_size,
            'uuid': self.order_uuid
        })
        
        # Verify error page structure
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'payments/error_page.html')
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], ERROR_MESSAGES['device_offline'])
        
        # Verify user-friendly message
        content = response.content.decode()
        self.assertIn(ERROR_MESSAGES['device_offline'], content)
    
    @patch('payments.services.validation_service.TmetrService')
    def test_error_page_rendering_for_heartbeat_check_failure(self, mock_tmetr_service_class):
        """Test error page renders correctly for heartbeat check failure."""
        # Mock Tmetr API to raise exception
        mock_tmetr_service = MagicMock()
        mock_tmetr_service_class.return_value = mock_tmetr_service
        
        import requests
        mock_tmetr_service.get_device_heartbeat.side_effect = requests.RequestException('API error')
        
        response = self.client.get('/v1/pay', {
            'deviceUuid': self.device_uuid,
            'drinkName': self.drink_name,
            'drinkNo': self.drink_number,
            'size': self.drink_size,
            'uuid': self.order_uuid
        })
        
        # Verify error page structure
        self.assertEqual(response.status_code, 400)
        self.assertTemplateUsed(response, 'payments/error_page.html')
        self.assertIn('error_message', response.context)
        self.assertEqual(response.context['error_message'], ERROR_MESSAGES['heartbeat_check_failed'])
        
        # Verify user-friendly message
        content = response.content.decode()
        self.assertIn(ERROR_MESSAGES['heartbeat_check_failed'], content)
        # Verify no technical details are exposed
        self.assertNotIn('RequestException', content)
        self.assertNotIn('API error', content)
