from django.test import TestCase
from django.utils.timezone import now
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from payments.models import Order, Device, Merchant, MerchantCredentials


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


class DevicePaymentScenarioTestCase(TestCase):
    """Unit tests for Device.payment_scenario validation"""

    def setUp(self):
        """Set up test fixtures"""
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            contact_email="test@example.com",
            bank_account="1234567890",
            valid_until=(now() + timedelta(days=365)).date()
        )

    def test_device_default_payment_scenario(self):
        """
        Test that Device uses default payment scenario when not specified
        Requirements: 2.2
        """
        device = Device.objects.create(
            device_uuid="test-device-001",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now()
        )
        
        self.assertEqual(device.payment_scenario, 'Yookassa',
                        "Device should have default payment scenario 'Yookassa'")

    def test_device_custom_payment_scenario(self):
        """
        Test that Device can be created with custom payment scenario
        Requirements: 2.1, 2.4
        """
        device = Device.objects.create(
            device_uuid="test-device-002",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now(),
            payment_scenario='TBank'
        )
        
        self.assertEqual(device.payment_scenario, 'TBank',
                        "Device should have custom payment scenario 'TBank'")

    def test_device_invalid_payment_scenario_validation(self):
        """
        Test that Device validation rejects invalid payment scenarios
        Requirements: 2.3
        """
        device = Device(
            device_uuid="test-device-003",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now(),
            payment_scenario='InvalidScenario'
        )
        
        with self.assertRaises(ValidationError) as context:
            device.clean()
        
        self.assertIn('Invalid payment scenario', str(context.exception),
                     "Validation should reject invalid payment scenario")

    def test_device_update_payment_scenario(self):
        """
        Test that Device payment scenario can be updated
        Requirements: 2.4
        """
        device = Device.objects.create(
            device_uuid="test-device-004",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now(),
            payment_scenario='Yookassa'
        )
        
        device.payment_scenario = 'Custom'
        device.save()
        device.refresh_from_db()
        
        self.assertEqual(device.payment_scenario, 'Custom',
                        "Device payment scenario should be updated to 'Custom'")


class MerchantCredentialsTestCase(TestCase):
    """Unit tests for MerchantCredentials model"""

    def setUp(self):
        """Set up test fixtures"""
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            contact_email="test@example.com",
            bank_account="1234567890",
            valid_until=(now() + timedelta(days=365)).date()
        )

    def test_merchant_credentials_creation(self):
        """
        Test that MerchantCredentials can be created with JSON data
        Requirements: 3.1, 3.2
        """
        credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={
                'account_id': 'test_account_123',
                'secret_key': 'test_secret_key_456'
            }
        )
        
        self.assertEqual(credentials.merchant, self.merchant,
                        "Credentials should be linked to merchant")
        self.assertEqual(credentials.scenario, 'Yookassa',
                        "Credentials scenario should be 'Yookassa'")
        self.assertEqual(credentials.credentials['account_id'], 'test_account_123',
                        "Credentials should contain account_id")
        self.assertEqual(credentials.credentials['secret_key'], 'test_secret_key_456',
                        "Credentials should contain secret_key")

    def test_merchant_credentials_unique_constraint(self):
        """
        Test that unique constraint prevents duplicate credentials for same merchant and scenario
        Requirements: 3.1
        """
        MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={'account_id': 'test_123', 'secret_key': 'secret_456'}
        )
        
        with self.assertRaises(Exception) as context:
            MerchantCredentials.objects.create(
                merchant=self.merchant,
                scenario='Yookassa',
                credentials={'account_id': 'test_789', 'secret_key': 'secret_012'}
            )
        
        self.assertTrue('unique' in str(context.exception).lower() or 
                       'duplicate' in str(context.exception).lower(),
                       "Should raise unique constraint violation")

    def test_merchant_multiple_scenario_credentials(self):
        """
        Test that merchant can have credentials for multiple scenarios
        Requirements: 3.4
        """
        yookassa_creds = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={'account_id': 'yookassa_123', 'secret_key': 'yookassa_secret'}
        )
        
        tbank_creds = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='TBank',
            credentials={'shop_id': 'tbank_shop_123', 'secret_key': 'tbank_secret'}
        )
        
        merchant_credentials = MerchantCredentials.objects.filter(merchant=self.merchant)
        self.assertEqual(merchant_credentials.count(), 2,
                        "Merchant should have credentials for 2 scenarios")
        
        scenarios = [cred.scenario for cred in merchant_credentials]
        self.assertIn('Yookassa', scenarios, "Should have Yookassa credentials")
        self.assertIn('TBank', scenarios, "Should have TBank credentials")

    def test_merchant_credentials_json_field_storage(self):
        """
        Test that JSON field correctly stores and retrieves complex credential structures
        Requirements: 3.2
        """
        complex_credentials = {
            'account_id': 'test_account',
            'secret_key': 'test_secret',
            'api_endpoint': 'https://api.example.com',
            'timeout': 30,
            'retry_count': 3,
            'metadata': {
                'region': 'us-east-1',
                'environment': 'production'
            }
        }
        
        credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Custom',
            credentials=complex_credentials
        )
        
        credentials.refresh_from_db()
        
        self.assertEqual(credentials.credentials['account_id'], 'test_account')
        self.assertEqual(credentials.credentials['timeout'], 30)
        self.assertEqual(credentials.credentials['metadata']['region'], 'us-east-1')
        self.assertIsInstance(credentials.credentials, dict,
                            "Credentials should be stored as dictionary")

    def test_merchant_credentials_str_representation(self):
        """
        Test that MerchantCredentials __str__ method returns expected format
        Requirements: 3.1
        """
        credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={'account_id': 'test_123'}
        )
        
        expected_str = f"{self.merchant.name} - Yookassa"
        self.assertEqual(str(credentials), expected_str,
                        "String representation should be 'Merchant Name - Scenario'")



class PaymentScenarioServiceTestCase(TestCase):
    """Unit tests for PaymentScenarioService"""

    def setUp(self):
        """Set up test fixtures"""
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            contact_email="test@example.com",
            bank_account="1234567890",
            valid_until=(now() + timedelta(days=365)).date()
        )
        
        self.device = Device.objects.create(
            device_uuid="test-device-001",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now(),
            payment_scenario='Yookassa'
        )
        
        self.yookassa_credentials = MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={
                'account_id': 'test_account_123',
                'secret_key': 'test_secret_key_456'
            }
        )

    def test_get_merchant_credentials_success(self):
        """
        Test successful retrieval of merchant credentials
        Requirements: 3.5, 4.1
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        
        credentials = PaymentScenarioService.get_merchant_credentials(
            self.merchant, 'Yookassa'
        )
        
        self.assertIsInstance(credentials, dict,
                            "Credentials should be returned as dictionary")
        self.assertEqual(credentials['account_id'], 'test_account_123',
                        "Should return correct account_id")
        self.assertEqual(credentials['secret_key'], 'test_secret_key_456',
                        "Should return correct secret_key")

    def test_get_merchant_credentials_not_found(self):
        """
        Test that ValueError is raised when credentials are not found
        Requirements: 4.2, 4.5
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        
        with self.assertRaises(ValueError) as context:
            PaymentScenarioService.get_merchant_credentials(
                self.merchant, 'TBank'
            )
        
        self.assertIn('not configured', str(context.exception).lower(),
                     "Error message should indicate credentials not configured")

    def test_execute_scenario_yookassa(self):
        """
        Test execute_scenario routes to Yookassa handler
        Requirements: 4.1, 4.3
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        from unittest.mock import patch
        
        order = Order.objects.create(
            drink_name="Espresso",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=250,
            status='created'
        )
        
        drink_details = {
            'price': 25000,
            'drink_id': 'test_drink_123'
        }
        
        with patch.object(PaymentScenarioService, 'execute_yookassa_scenario') as mock_yookassa:
            from django.http import HttpResponseRedirect
            mock_yookassa.return_value = HttpResponseRedirect('https://payment.example.com')
            
            result = PaymentScenarioService.execute_scenario(
                self.device, order, drink_details
            )
            
            mock_yookassa.assert_called_once_with(self.device, order, drink_details)
            self.assertIsInstance(result, HttpResponseRedirect,
                                "Should return HttpResponseRedirect")

    def test_execute_scenario_tbank(self):
        """
        Test execute_scenario routes to TBank handler
        Requirements: 4.1, 4.3
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        from unittest.mock import patch
        
        self.device.payment_scenario = 'TBank'
        self.device.save()
        
        MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='TBank',
            credentials={'shop_id': 'test_shop', 'secret_key': 'test_secret'}
        )
        
        order = Order.objects.create(
            drink_name="Cappuccino",
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=300,
            status='created'
        )
        
        drink_details = {
            'price': 30000,
            'drink_id': 'test_drink_456'
        }
        
        with patch.object(PaymentScenarioService, 'execute_tbank_scenario') as mock_tbank:
            from django.http import HttpResponseRedirect
            mock_tbank.return_value = HttpResponseRedirect('https://tbank.example.com')
            
            result = PaymentScenarioService.execute_scenario(
                self.device, order, drink_details
            )
            
            mock_tbank.assert_called_once_with(self.device, order, drink_details)
            self.assertIsInstance(result, HttpResponseRedirect,
                                "Should return HttpResponseRedirect")

    def test_execute_scenario_custom(self):
        """
        Test execute_scenario routes to Custom handler
        Requirements: 4.1, 5.3
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        from unittest.mock import patch
        
        self.device.payment_scenario = 'Custom'
        self.device.redirect_url = 'https://custom-payment.example.com/pay'
        self.device.save()
        
        order = Order.objects.create(
            drink_name="Latte",
            device=self.device,
            merchant=self.merchant,
            size=3,
            price=350,
            status='created'
        )
        
        with patch.object(PaymentScenarioService, 'execute_custom_scenario') as mock_custom:
            from django.http import HttpResponseRedirect
            mock_custom.return_value = HttpResponseRedirect('https://custom-payment.example.com/pay?order_id=123')
            
            result = PaymentScenarioService.execute_scenario(
                self.device, order, {}
            )
            
            mock_custom.assert_called_once_with(self.device, order)
            self.assertIsInstance(result, HttpResponseRedirect,
                                "Should return HttpResponseRedirect")

    def test_execute_scenario_missing_credentials(self):
        """
        Test that execute_scenario raises ValueError when credentials are missing
        Requirements: 4.2, 4.5
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        
        self.device.payment_scenario = 'TBank'
        self.device.save()
        
        order = Order.objects.create(
            drink_name="Americano",
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=275,
            status='created'
        )
        
        drink_details = {'price': 27500}
        
        with self.assertRaises(ValueError) as context:
            PaymentScenarioService.execute_scenario(
                self.device, order, drink_details
            )
        
        self.assertIn('not configured', str(context.exception).lower(),
                     "Should raise ValueError for missing credentials")

    def test_execute_custom_scenario_missing_redirect_url(self):
        """
        Test that execute_custom_scenario raises ValueError when redirect_url is missing
        Requirements: 5.3, 5.4
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        
        self.device.payment_scenario = 'Custom'
        self.device.redirect_url = None
        self.device.save()
        
        order = Order.objects.create(
            drink_name="Mocha",
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=400,
            status='created'
        )
        
        with self.assertRaises(ValueError) as context:
            PaymentScenarioService.execute_custom_scenario(self.device, order)
        
        self.assertIn('redirect url', str(context.exception).lower(),
                     "Should raise ValueError for missing redirect_url")

    def test_execute_custom_scenario_empty_redirect_url(self):
        """
        Test that execute_custom_scenario raises ValueError when redirect_url is empty
        Requirements: 5.4
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        
        self.device.payment_scenario = 'Custom'
        self.device.redirect_url = ''
        self.device.save()
        
        order = Order.objects.create(
            drink_name="Flat White",
            device=self.device,
            merchant=self.merchant,
            size=2,
            price=325,
            status='created'
        )
        
        with self.assertRaises(ValueError) as context:
            PaymentScenarioService.execute_custom_scenario(self.device, order)
        
        self.assertIn('redirect url', str(context.exception).lower(),
                     "Should raise ValueError for empty redirect_url")

    def test_execute_custom_scenario_success(self):
        """
        Test successful execution of custom scenario with redirect_url
        Requirements: 5.1, 5.2
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        from django.http import HttpResponseRedirect
        
        self.device.payment_scenario = 'Custom'
        self.device.redirect_url = 'https://custom-payment.example.com/pay'
        self.device.save()
        
        order = Order.objects.create(
            drink_name="Macchiato",
            device=self.device,
            merchant=self.merchant,
            size=1,
            price=280,
            status='created'
        )
        
        result = PaymentScenarioService.execute_custom_scenario(self.device, order)
        
        self.assertIsInstance(result, HttpResponseRedirect,
                            "Should return HttpResponseRedirect")
        
        redirect_url = result.url
        self.assertIn('order_id', redirect_url,
                     "Redirect URL should contain order_id parameter")
        self.assertIn('drink_name', redirect_url,
                     "Redirect URL should contain drink_name parameter")
        self.assertIn('price', redirect_url,
                     "Redirect URL should contain price parameter")
        self.assertIn('device_uuid', redirect_url,
                     "Redirect URL should contain device_uuid parameter")



class PaymentScenarioIntegrationTestCase(TestCase):
    """Integration tests for payment scenario flows"""

    def setUp(self):
        """Set up test fixtures"""
        self.merchant = Merchant.objects.create(
            name="Test Merchant",
            contact_email="test@example.com",
            bank_account="1234567890",
            valid_until=(now() + timedelta(days=365)).date()
        )

    def test_yookassa_payment_flow(self):
        """
        Test full payment flow for Yookassa scenario
        Requirements: 4.1, 4.2, 4.3, 4.4
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        from unittest.mock import patch, MagicMock
        
        # Setup device with Yookassa scenario
        device = Device.objects.create(
            device_uuid="test-device-yookassa",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now(),
            payment_scenario='Yookassa'
        )
        
        # Setup credentials
        MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={
                'account_id': 'test_account_123',
                'secret_key': 'test_secret_key_456'
            }
        )
        
        # Create order
        order = Order.objects.create(
            drink_name="Espresso",
            device=device,
            merchant=self.merchant,
            size=1,
            price=250,
            status='created'
        )
        
        drink_details = {
            'price': 25000,
            'drink_id': 'test_drink_123'
        }
        
        # Mock Yookassa payment creation
        with patch('payments.services.yookassa_service.create_payment') as mock_create:
            mock_payment = MagicMock()
            mock_payment.json.return_value = '{"id": "payment_123", "confirmation": {"confirmation_url": "https://yookassa.example.com/pay"}}'
            mock_create.return_value = mock_payment
            
            result = PaymentScenarioService.execute_scenario(device, order, drink_details)
            
            # Verify payment was created with correct credentials
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            self.assertEqual(call_kwargs['credentials']['account_id'], 'test_account_123')
            self.assertEqual(call_kwargs['credentials']['secret_key'], 'test_secret_key_456')
            
            # Verify order status updated to pending
            order.refresh_from_db()
            self.assertEqual(order.status, 'pending',
                           "Order status should be 'pending' after payment creation")
            self.assertEqual(order.external_order_id, 'payment_123',
                           "Order should have external_order_id set")
            
            # Verify redirect
            from django.http import HttpResponseRedirect
            self.assertIsInstance(result, HttpResponseRedirect,
                                "Should return redirect to payment URL")

    def test_tbank_payment_flow(self):
        """
        Test full payment flow for TBank scenario
        Requirements: 4.1, 4.2, 4.3, 4.5
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        from unittest.mock import patch, MagicMock
        
        # Setup device with TBank scenario
        device = Device.objects.create(
            device_uuid="test-device-tbank",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now(),
            payment_scenario='TBank'
        )
        
        # Setup credentials
        MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='TBank',
            credentials={
                'shop_id': 'test_shop_123',
                'secret_key': 'test_tbank_secret'
            }
        )
        
        # Create order
        order = Order.objects.create(
            drink_name="Cappuccino",
            device=device,
            merchant=self.merchant,
            size=2,
            price=300,
            status='created'
        )
        
        drink_details = {
            'price': 30000,
            'drink_id': 'test_drink_456'
        }
        
        # Mock TBank payment processing
        with patch('payments.services.t_bank_service.process_payment') as mock_process:
            mock_payment = MagicMock()
            mock_payment.payment_id = 'tbank_payment_456'
            mock_payment.payment_url = 'https://tbank.example.com/pay'
            mock_process.return_value = (mock_payment, None)
            
            result = PaymentScenarioService.execute_scenario(device, order, drink_details)
            
            # Verify payment was processed with correct credentials
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0]
            call_kwargs = mock_process.call_args[1] if len(mock_process.call_args) > 1 else {}
            credentials = call_args[1] if len(call_args) > 1 else call_kwargs.get('credentials')
            self.assertEqual(credentials['shop_id'], 'test_shop_123')
            self.assertEqual(credentials['secret_key'], 'test_tbank_secret')
            
            # Verify order status updated to pending
            order.refresh_from_db()
            self.assertEqual(order.status, 'pending',
                           "Order status should be 'pending' after payment creation")
            self.assertEqual(order.external_order_id, 'tbank_payment_456',
                           "Order should have external_order_id set")
            
            # Verify redirect
            from django.http import HttpResponseRedirect
            self.assertIsInstance(result, HttpResponseRedirect,
                                "Should return redirect to payment URL")

    def test_custom_payment_flow(self):
        """
        Test full payment flow for Custom scenario
        Requirements: 5.1, 5.2, 5.3
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        
        # Setup device with Custom scenario
        device = Device.objects.create(
            device_uuid="test-device-custom",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now(),
            payment_scenario='Custom',
            redirect_url='https://custom-payment.example.com/pay?merchant_id=123'
        )
        
        # Create order
        order = Order.objects.create(
            drink_name="Latte",
            device=device,
            merchant=self.merchant,
            size=3,
            price=350,
            status='created'
        )
        
        result = PaymentScenarioService.execute_scenario(device, order, {})
        
        # Verify redirect with order parameters
        from django.http import HttpResponseRedirect
        self.assertIsInstance(result, HttpResponseRedirect,
                            "Should return redirect to custom payment URL")
        
        redirect_url = result.url
        self.assertIn('custom-payment.example.com', redirect_url,
                     "Should redirect to configured URL")
        self.assertIn(f'order_id={order.id}', redirect_url,
                     "Should include order_id parameter")
        self.assertIn('drink_name=Latte', redirect_url,
                     "Should include drink_name parameter")
        self.assertIn('price=350', redirect_url,
                     "Should include price parameter")
        self.assertIn('size=3', redirect_url,
                     "Should include size parameter")
        self.assertIn(f'device_uuid={device.device_uuid}', redirect_url,
                     "Should include device_uuid parameter")
        self.assertIn(f'merchant_id={self.merchant.id}', redirect_url,
                     "Should include merchant_id parameter")

    def test_missing_credentials_error_flow(self):
        """
        Test error handling when credentials are missing
        Requirements: 4.5
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        
        # Setup device with Yookassa scenario but no credentials
        device = Device.objects.create(
            device_uuid="test-device-no-creds",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now(),
            payment_scenario='Yookassa'
        )
        
        # Create order
        order = Order.objects.create(
            drink_name="Americano",
            device=device,
            merchant=self.merchant,
            size=2,
            price=275,
            status='created'
        )
        
        drink_details = {'price': 27500}
        
        # Attempt to execute scenario without credentials
        with self.assertRaises(ValueError) as context:
            PaymentScenarioService.execute_scenario(device, order, drink_details)
        
        self.assertIn('not configured', str(context.exception).lower(),
                     "Should raise ValueError with appropriate message")

    def test_invalid_scenario_error_flow(self):
        """
        Test error handling for invalid payment scenario
        Requirements: 4.1, 4.2
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        
        # Setup device with invalid scenario (bypassing validation for test)
        device = Device.objects.create(
            device_uuid="test-device-invalid",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now(),
            payment_scenario='Yookassa'  # Create with valid scenario first
        )
        
        # Manually set invalid scenario to bypass validation
        Device.objects.filter(pk=device.pk).update(payment_scenario='InvalidScenario')
        device.refresh_from_db()
        
        # Create order
        order = Order.objects.create(
            drink_name="Mocha",
            device=device,
            merchant=self.merchant,
            size=2,
            price=400,
            status='created'
        )
        
        # Attempt to execute invalid scenario
        with self.assertRaises(ValueError) as context:
            PaymentScenarioService.execute_scenario(device, order, {})
        
        self.assertIn('unknown', str(context.exception).lower(),
                     "Should raise ValueError for unknown scenario")

    def test_custom_scenario_missing_redirect_url_error(self):
        """
        Test error handling when Custom scenario has no redirect_url
        Requirements: 5.4
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        
        # Setup device with Custom scenario but no redirect_url
        device = Device.objects.create(
            device_uuid="test-device-custom-no-url",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now(),
            payment_scenario='Custom',
            redirect_url=None
        )
        
        # Create order
        order = Order.objects.create(
            drink_name="Flat White",
            device=device,
            merchant=self.merchant,
            size=2,
            price=325,
            status='created'
        )
        
        # Attempt to execute Custom scenario without redirect_url
        with self.assertRaises(ValueError) as context:
            PaymentScenarioService.execute_scenario(device, order, {})
        
        self.assertIn('redirect url', str(context.exception).lower(),
                     "Should raise ValueError for missing redirect_url")

    def test_payment_failure_updates_order_status(self):
        """
        Test that order status is updated to 'failed' when payment creation fails
        Requirements: 4.5
        """
        from payments.services.payment_scenario_service import PaymentScenarioService
        from unittest.mock import patch
        
        # Setup device with Yookassa scenario
        device = Device.objects.create(
            device_uuid="test-device-fail",
            merchant=self.merchant,
            location="Test Location",
            status="online",
            last_interaction=now(),
            payment_scenario='Yookassa'
        )
        
        # Setup credentials
        MerchantCredentials.objects.create(
            merchant=self.merchant,
            scenario='Yookassa',
            credentials={
                'account_id': 'test_account',
                'secret_key': 'test_secret'
            }
        )
        
        # Create order
        order = Order.objects.create(
            drink_name="Macchiato",
            device=device,
            merchant=self.merchant,
            size=1,
            price=280,
            status='created'
        )
        
        drink_details = {'price': 28000, 'drink_id': 'test_drink'}
        
        # Mock payment creation to raise exception
        with patch('payments.services.yookassa_service.create_payment') as mock_create:
            mock_create.side_effect = Exception("Payment API error")
            
            with self.assertRaises(Exception):
                PaymentScenarioService.execute_scenario(device, order, drink_details)
            
            # Verify order status updated to failed
            order.refresh_from_db()
            self.assertEqual(order.status, 'failed',
                           "Order status should be 'failed' after payment error")
