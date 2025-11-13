"""
Unit tests for OrderValidationService.
Tests validation chain execution with early termination on failure.
"""
import uuid
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.utils.timezone import now
from payments.models import Merchant, Device, Order
from payments.services.validation_service import OrderValidationService
from payments.user_messages import ERROR_MESSAGES


class OrderValidationServiceTestCase(TestCase):
    """Base test case with fixtures for OrderValidationService tests."""
    
    def setUp(self):
        """Set up test fixtures for Merchant, Device, and Orders."""
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
        
        # Create test order UUID
        self.order_uuid = str(uuid.uuid4())
        self.device_uuid = 'test-device-uuid'


class ValidateRequestHashTests(OrderValidationServiceTestCase):
    """Tests for validate_request_hash() placeholder implementation."""
    
    def test_validate_request_hash_returns_success(self):
        """Test placeholder implementation always returns success."""
        request_params = {
            'deviceUuid': 'test-device',
            'drinkName': 'Cappuccino',
            'uuid': str(uuid.uuid4())
        }
        
        is_valid, error_message = OrderValidationService.validate_request_hash(request_params)
        
        self.assertTrue(is_valid)
        self.assertIsNone(error_message)
    
    def test_validate_request_hash_logs_parameters(self):
        """Test hash validation logs request parameters."""
        request_params = {
            'deviceUuid': 'test-device',
            'drinkName': 'Latte',
            'uuid': str(uuid.uuid4()),
            'size': '1'
        }
        
        with self.assertLogs('payments.services.validation_service', level='INFO') as logs:
            OrderValidationService.validate_request_hash(request_params)
        
        # Verify logging occurred
        self.assertTrue(any('validate_request_hash' in log for log in logs.output))
        self.assertTrue(any('placeholder' in log for log in logs.output))


class CheckOrderExistenceTests(OrderValidationServiceTestCase):
    """Tests for check_order_existence() covering all scenarios."""
    
    def test_check_order_existence_non_existent_order(self):
        """Test non-existent order returns should_create_new=True."""
        non_existent_uuid = str(uuid.uuid4())
        
        should_create_new, error_message, existing_order = \
            OrderValidationService.check_order_existence(non_existent_uuid)
        
        self.assertTrue(should_create_new)
        self.assertIsNone(error_message)
        self.assertIsNone(existing_order)
    
    def test_check_order_existence_existing_valid_order(self):
        """Test existing order with status 'created' and not expired returns existing order."""
        # Create order with 'created' status and future expiration
        order = Order.objects.create(
            id=self.order_uuid,
            device=self.device,
            merchant=self.merchant,
            drink_name='Cappuccino',
            size=2,
            price=5000,
            status='created',
            expires_at=now() + timedelta(minutes=10)
        )
        
        should_create_new, error_message, existing_order = \
            OrderValidationService.check_order_existence(str(order.id))
        
        self.assertFalse(should_create_new)
        self.assertIsNone(error_message)
        self.assertIsNotNone(existing_order)
        self.assertEqual(str(existing_order.id), str(order.id))
        self.assertEqual(existing_order.status, 'created')
    
    def test_check_order_existence_expired_order(self):
        """Test existing order with expired expires_at returns error."""
        # Create order with past expiration
        order = Order.objects.create(
            id=self.order_uuid,
            device=self.device,
            merchant=self.merchant,
            drink_name='Latte',
            size=2,
            price=6000,
            status='created',
            expires_at=now() - timedelta(minutes=5)
        )
        
        should_create_new, error_message, existing_order = \
            OrderValidationService.check_order_existence(str(order.id))
        
        self.assertFalse(should_create_new)
        self.assertEqual(error_message, ERROR_MESSAGES['order_expired'])
        self.assertIsNone(existing_order)
    
    def test_check_order_existence_order_with_different_status(self):
        """Test existing order with status other than 'created' returns should_create_new=True."""
        # Create order with 'paid' status
        order = Order.objects.create(
            id=self.order_uuid,
            device=self.device,
            merchant=self.merchant,
            drink_name='Espresso',
            size=1,
            price=4000,
            status='paid',
            expires_at=now() + timedelta(minutes=10)
        )
        
        should_create_new, error_message, existing_order = \
            OrderValidationService.check_order_existence(str(order.id))
        
        self.assertTrue(should_create_new)
        self.assertIsNone(error_message)
        self.assertIsNone(existing_order)
    
    def test_check_order_existence_logs_results(self):
        """Test order existence check logs all results."""
        non_existent_uuid = str(uuid.uuid4())
        
        with self.assertLogs('payments.services.validation_service', level='INFO') as logs:
            OrderValidationService.check_order_existence(non_existent_uuid)
        
        # Verify logging occurred
        self.assertTrue(any('check_order_existence' in log for log in logs.output))
        self.assertTrue(any('not found' in log.lower() for log in logs.output))


class CheckDeviceOnlineStatusTests(OrderValidationServiceTestCase):
    """Tests for check_device_online_status() covering online/offline cases and error handling."""
    
    @patch('payments.services.validation_service.TmetrService')
    @override_settings(DEVICE_ONLINE_THRESHOLD_MINUTES=5)
    def test_check_device_online_status_device_online(self, mock_tmetr_service_class):
        """Test device online when heartbeat within threshold."""
        # Mock Tmetr API response with recent heartbeat
        mock_tmetr_service = MagicMock()
        mock_tmetr_service_class.return_value = mock_tmetr_service
        
        recent_heartbeat = int((now() - timedelta(minutes=2)).timestamp())
        mock_tmetr_service.get_device_heartbeat.return_value = {
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
        
        is_online, error_message = OrderValidationService.check_device_online_status(self.device_uuid)
        
        self.assertTrue(is_online)
        self.assertIsNone(error_message)
        mock_tmetr_service.get_device_heartbeat.assert_called_once_with(self.device_uuid)
    
    @patch('payments.services.validation_service.TmetrService')
    @override_settings(DEVICE_ONLINE_THRESHOLD_MINUTES=5)
    def test_check_device_online_status_device_offline(self, mock_tmetr_service_class):
        """Test device offline when heartbeat exceeds threshold."""
        # Mock Tmetr API response with old heartbeat
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
        
        is_online, error_message = OrderValidationService.check_device_online_status(self.device_uuid)
        
        self.assertFalse(is_online)
        self.assertEqual(error_message, ERROR_MESSAGES['device_offline'])
    
    @patch('payments.services.validation_service.TmetrService')
    def test_check_device_online_status_no_heartbeat_data(self, mock_tmetr_service_class):
        """Test device offline when no heartbeat data found."""
        # Mock Tmetr API response with empty content
        mock_tmetr_service = MagicMock()
        mock_tmetr_service_class.return_value = mock_tmetr_service
        
        mock_tmetr_service.get_device_heartbeat.return_value = {
            'content': [],
            'totalElements': 0,
            'offset': 0,
            'limit': 1
        }
        
        is_online, error_message = OrderValidationService.check_device_online_status(self.device_uuid)
        
        self.assertFalse(is_online)
        self.assertEqual(error_message, ERROR_MESSAGES['device_offline'])
    
    @patch('payments.services.validation_service.TmetrService')
    def test_check_device_online_status_missing_heartbeat_timestamp(self, mock_tmetr_service_class):
        """Test heartbeat check failed when timestamp is missing."""
        # Mock Tmetr API response with missing heartbeatCreatedAt
        mock_tmetr_service = MagicMock()
        mock_tmetr_service_class.return_value = mock_tmetr_service
        
        mock_tmetr_service.get_device_heartbeat.return_value = {
            'content': [
                {
                    'deviceId': self.device_uuid,
                    'deviceIotName': 'test-device'
                    # heartbeatCreatedAt is missing
                }
            ],
            'totalElements': 1,
            'offset': 0,
            'limit': 1
        }
        
        is_online, error_message = OrderValidationService.check_device_online_status(self.device_uuid)
        
        self.assertFalse(is_online)
        self.assertEqual(error_message, ERROR_MESSAGES['heartbeat_check_failed'])
    
    @patch('payments.services.validation_service.TmetrService')
    def test_check_device_online_status_api_error(self, mock_tmetr_service_class):
        """Test heartbeat check failed when Tmetr API raises exception."""
        # Mock Tmetr API to raise exception
        mock_tmetr_service = MagicMock()
        mock_tmetr_service_class.return_value = mock_tmetr_service
        
        import requests
        mock_tmetr_service.get_device_heartbeat.side_effect = requests.RequestException('API connection error')
        
        is_online, error_message = OrderValidationService.check_device_online_status(self.device_uuid)
        
        self.assertFalse(is_online)
        self.assertEqual(error_message, ERROR_MESSAGES['heartbeat_check_failed'])
    
    @patch('payments.services.validation_service.TmetrService')
    @override_settings(DEVICE_ONLINE_THRESHOLD_MINUTES=5)
    def test_check_device_online_status_logs_details(self, mock_tmetr_service_class):
        """Test device status check logs device UUID, heartbeat timestamp, and determination."""
        # Mock Tmetr API response
        mock_tmetr_service = MagicMock()
        mock_tmetr_service_class.return_value = mock_tmetr_service
        
        recent_heartbeat = int((now() - timedelta(minutes=2)).timestamp())
        mock_tmetr_service.get_device_heartbeat.return_value = {
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
        
        with self.assertLogs('payments.services.validation_service', level='INFO') as logs:
            OrderValidationService.check_device_online_status(self.device_uuid)
        
        # Verify comprehensive logging
        log_output = ' '.join(logs.output)
        self.assertIn('check_device_online_status', log_output)
        self.assertIn(self.device_uuid, log_output)
        self.assertIn('online', log_output.lower())


class ExecuteValidationChainTests(OrderValidationServiceTestCase):
    """Tests for execute_validation_chain() covering early termination and successful execution."""
    
    @patch('payments.services.validation_service.OrderValidationService.check_device_online_status')
    @patch('payments.services.validation_service.OrderValidationService.check_order_existence')
    @patch('payments.services.validation_service.OrderValidationService.validate_request_hash')
    def test_execute_validation_chain_all_validations_pass(
        self,
        mock_validate_hash,
        mock_check_order,
        mock_check_device
    ):
        """Test successful validation chain execution when all validations pass."""
        # Mock all validations to pass
        mock_validate_hash.return_value = (True, None)
        mock_check_order.return_value = (True, None, None)  # Should create new order
        mock_check_device.return_value = (True, None)
        
        request_params = {
            'deviceUuid': self.device_uuid,
            'drinkName': 'Cappuccino',
            'uuid': self.order_uuid
        }
        
        result = OrderValidationService.execute_validation_chain(
            request_params=request_params,
            device_uuid=self.device_uuid,
            order_id=self.order_uuid
        )
        
        self.assertTrue(result['valid'])
        self.assertIsNone(result['error_message'])
        self.assertIsNone(result['existing_order'])
        self.assertTrue(result['should_create_new_order'])
        
        # Verify all validations were called
        mock_validate_hash.assert_called_once_with(request_params)
        mock_check_order.assert_called_once_with(self.order_uuid)
        mock_check_device.assert_called_once_with(self.device_uuid)
    
    @patch('payments.services.validation_service.OrderValidationService.check_device_online_status')
    @patch('payments.services.validation_service.OrderValidationService.check_order_existence')
    @patch('payments.services.validation_service.OrderValidationService.validate_request_hash')
    def test_execute_validation_chain_early_termination_on_hash_failure(
        self,
        mock_validate_hash,
        mock_check_order,
        mock_check_device
    ):
        """Test validation chain terminates early on hash validation failure."""
        # Mock hash validation to fail
        mock_validate_hash.return_value = (False, ERROR_MESSAGES['invalid_request_hash'])
        
        request_params = {
            'deviceUuid': self.device_uuid,
            'drinkName': 'Cappuccino',
            'uuid': self.order_uuid
        }
        
        result = OrderValidationService.execute_validation_chain(
            request_params=request_params,
            device_uuid=self.device_uuid,
            order_id=self.order_uuid
        )
        
        self.assertFalse(result['valid'])
        self.assertEqual(result['error_message'], ERROR_MESSAGES['invalid_request_hash'])
        self.assertIsNone(result['existing_order'])
        self.assertFalse(result['should_create_new_order'])
        
        # Verify subsequent validations were NOT called
        mock_validate_hash.assert_called_once()
        mock_check_order.assert_not_called()
        mock_check_device.assert_not_called()
    
    @patch('payments.services.validation_service.OrderValidationService.check_device_online_status')
    @patch('payments.services.validation_service.OrderValidationService.check_order_existence')
    @patch('payments.services.validation_service.OrderValidationService.validate_request_hash')
    def test_execute_validation_chain_early_termination_on_order_failure(
        self,
        mock_validate_hash,
        mock_check_order,
        mock_check_device
    ):
        """Test validation chain terminates early on order validation failure."""
        # Mock hash validation to pass, order validation to fail
        mock_validate_hash.return_value = (True, None)
        mock_check_order.return_value = (False, ERROR_MESSAGES['order_expired'], None)
        
        request_params = {
            'deviceUuid': self.device_uuid,
            'drinkName': 'Cappuccino',
            'uuid': self.order_uuid
        }
        
        result = OrderValidationService.execute_validation_chain(
            request_params=request_params,
            device_uuid=self.device_uuid,
            order_id=self.order_uuid
        )
        
        self.assertFalse(result['valid'])
        self.assertEqual(result['error_message'], ERROR_MESSAGES['order_expired'])
        self.assertIsNone(result['existing_order'])
        self.assertFalse(result['should_create_new_order'])
        
        # Verify device check was NOT called
        mock_validate_hash.assert_called_once()
        mock_check_order.assert_called_once()
        mock_check_device.assert_not_called()
    
    @patch('payments.services.validation_service.OrderValidationService.check_device_online_status')
    @patch('payments.services.validation_service.OrderValidationService.check_order_existence')
    @patch('payments.services.validation_service.OrderValidationService.validate_request_hash')
    def test_execute_validation_chain_early_termination_on_device_failure(
        self,
        mock_validate_hash,
        mock_check_order,
        mock_check_device
    ):
        """Test validation chain terminates on device status check failure."""
        # Mock hash and order validations to pass, device check to fail
        mock_validate_hash.return_value = (True, None)
        mock_check_order.return_value = (True, None, None)
        mock_check_device.return_value = (False, ERROR_MESSAGES['device_offline'])
        
        request_params = {
            'deviceUuid': self.device_uuid,
            'drinkName': 'Cappuccino',
            'uuid': self.order_uuid
        }
        
        result = OrderValidationService.execute_validation_chain(
            request_params=request_params,
            device_uuid=self.device_uuid,
            order_id=self.order_uuid
        )
        
        self.assertFalse(result['valid'])
        self.assertEqual(result['error_message'], ERROR_MESSAGES['device_offline'])
        self.assertIsNone(result['existing_order'])
        self.assertFalse(result['should_create_new_order'])
        
        # Verify all validations were called in sequence
        mock_validate_hash.assert_called_once()
        mock_check_order.assert_called_once()
        mock_check_device.assert_called_once()
    
    @patch('payments.services.validation_service.OrderValidationService.check_device_online_status')
    @patch('payments.services.validation_service.OrderValidationService.check_order_existence')
    @patch('payments.services.validation_service.OrderValidationService.validate_request_hash')
    def test_execute_validation_chain_with_existing_valid_order(
        self,
        mock_validate_hash,
        mock_check_order,
        mock_check_device
    ):
        """Test validation chain with existing valid order returns order and should_create_new_order=False."""
        # Create existing order
        existing_order = Order.objects.create(
            id=self.order_uuid,
            device=self.device,
            merchant=self.merchant,
            drink_name='Cappuccino',
            size=2,
            price=5000,
            status='created',
            expires_at=now() + timedelta(minutes=10)
        )
        
        # Mock validations
        mock_validate_hash.return_value = (True, None)
        mock_check_order.return_value = (False, None, existing_order)  # Existing valid order
        mock_check_device.return_value = (True, None)
        
        request_params = {
            'deviceUuid': self.device_uuid,
            'drinkName': 'Cappuccino',
            'uuid': self.order_uuid
        }
        
        result = OrderValidationService.execute_validation_chain(
            request_params=request_params,
            device_uuid=self.device_uuid,
            order_id=self.order_uuid
        )
        
        self.assertTrue(result['valid'])
        self.assertIsNone(result['error_message'])
        self.assertIsNotNone(result['existing_order'])
        self.assertEqual(result['existing_order'].id, existing_order.id)
        self.assertFalse(result['should_create_new_order'])
    
    @patch('payments.services.validation_service.OrderValidationService.check_device_online_status')
    @patch('payments.services.validation_service.OrderValidationService.check_order_existence')
    @patch('payments.services.validation_service.OrderValidationService.validate_request_hash')
    def test_execute_validation_chain_logs_start_and_completion(
        self,
        mock_validate_hash,
        mock_check_order,
        mock_check_device
    ):
        """Test validation chain logs start and completion."""
        # Mock all validations to pass
        mock_validate_hash.return_value = (True, None)
        mock_check_order.return_value = (True, None, None)
        mock_check_device.return_value = (True, None)
        
        request_params = {
            'deviceUuid': self.device_uuid,
            'drinkName': 'Cappuccino',
            'uuid': self.order_uuid
        }
        
        with self.assertLogs('payments.services.validation_service', level='INFO') as logs:
            OrderValidationService.execute_validation_chain(
                request_params=request_params,
                device_uuid=self.device_uuid,
                order_id=self.order_uuid
            )
        
        # Verify logging
        log_output = ' '.join(logs.output)
        self.assertIn('execute_validation_chain', log_output)
        self.assertIn('Starting validation chain', log_output)
        self.assertIn('completed successfully', log_output.lower())
        self.assertIn(self.device_uuid, log_output)
        self.assertIn(self.order_uuid, log_output)
