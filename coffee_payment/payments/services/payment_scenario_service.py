import json
from django.http import HttpResponseRedirect
from django.shortcuts import render
from payments.models import MerchantCredentials, Order
from payments.utils.logging import log_error, log_info
from payments.services import yookassa_service, t_bank_service


class PaymentScenarioService:
    """
    Service for managing payment scenario execution.
    Routes payment processing to appropriate payment provider based on device configuration.
    """
    
    @staticmethod
    def get_merchant_credentials(merchant, scenario):
        """
        Retrieves merchant credentials for the specified payment scenario.
        
        Args:
            merchant: Merchant instance
            scenario: Payment scenario name (e.g., 'Yookassa', 'TBank', 'Custom')
            
        Returns:
            dict: Credentials JSON data
            
        Raises:
            ValueError: If credentials not found for the merchant and scenario
        """
        try:
            credentials_obj = MerchantCredentials.objects.get(
                merchant=merchant,
                scenario=scenario
            )
            log_info(
                f"Retrieved credentials for Merchant {merchant.id}, scenario: {scenario}",
                'payment_scenario_service'
            )
            return credentials_obj.credentials
        except MerchantCredentials.DoesNotExist:
            error_msg = f"Payment credentials not configured for merchant {merchant.name} and scenario {scenario}"
            log_error(
                f"Missing credentials for Merchant {merchant.id}, scenario: {scenario}",
                'payment_scenario_service',
                'ERROR'
            )
            raise ValueError(error_msg)

    @staticmethod
    def execute_scenario(device, order, drink_details):
        """
        Routes payment processing to the appropriate scenario handler based on device configuration.
        
        Args:
            device: Device instance with payment_scenario configured
            order: Order instance with status='created'
            drink_details: Dict containing drink information (price, name, etc.)
            
        Returns:
            HttpResponse: Redirect to payment page or error page
            
        Raises:
            ValueError: If credentials are missing or configuration is invalid
        """
        scenario = device.payment_scenario
        merchant = device.merchant
        
        log_info(
            f"Device {device.device_uuid} using payment scenario: {scenario}",
            'payment_scenario_service'
        )
        
        try:
            if scenario == 'Yookassa':
                return PaymentScenarioService.execute_yookassa_scenario(
                    device, order, drink_details
                )
            elif scenario == 'TBank':
                return PaymentScenarioService.execute_tbank_scenario(
                    device, order, drink_details
                )
            elif scenario == 'Custom':
                return PaymentScenarioService.execute_custom_scenario(
                    device, order
                )
            else:
                error_msg = f"Unknown payment scenario: {scenario}"
                log_error(
                    f"Unknown scenario {scenario} for Device {device.device_uuid}",
                    'payment_scenario_service',
                    'ERROR'
                )
                raise ValueError(error_msg)
        except ValueError as e:
            # Re-raise ValueError for missing credentials or configuration
            raise
        except Exception as e:
            error_msg = f"Failed to execute payment scenario: {str(e)}"
            log_error(
                f"Error executing scenario {scenario} for Order {order.id}: {str(e)}",
                'payment_scenario_service',
                'ERROR'
            )
            raise Exception(error_msg)

    @staticmethod
    def execute_yookassa_scenario(device, order, drink_details):
        """
        Executes Yookassa payment scenario.
        
        Args:
            device: Device instance
            order: Order instance with status='created'
            drink_details: Dict containing drink information
            
        Returns:
            HttpResponseRedirect: Redirect to Yookassa payment page
            
        Raises:
            ValueError: If Yookassa credentials are missing
        """
        merchant = device.merchant
        
        # Get Yookassa credentials
        credentials = PaymentScenarioService.get_merchant_credentials(
            merchant, 'Yookassa'
        )
        
        # Extract drink information
        drink_price = drink_details.get('price', 5000)
        drink_name = order.drink_name
        drink_number = drink_details.get('drink_id', 'unknown')
        order_uuid = str(order.id)
        drink_size = str(order.size - 1)  # Convert back to 0-indexed
        
        log_info(
            f"Processing Yookassa payment for Order {order.id}. "
            f"Request params: device_id={device.device_uuid}, "
            f"drink_name={drink_name}, price={drink_price}, size={drink_size}",
            'payment_scenario_service'
        )
        
        try:
            # Build return URL to order status page
            from django.conf import settings
            domain = settings.BASE_URL
            return_url = f"https://{domain}/v1/order-status-page?order_id={order_uuid}"
            
            # Create payment with merchant-specific credentials
            payment = yookassa_service.create_payment(
                amount=drink_price / 100,
                description=f'Оплата напитка: {drink_name}',
                return_url=return_url,
                drink_no=drink_number,
                order_uuid=order_uuid,
                size=drink_size,
                credentials=credentials
            )
            
            payment_data = json.loads(payment.json())
            payment_id = payment_data['id']
            
            # Update order with payment information and change status to 'pending'
            order.payment_reference_id = payment_id
            order.status = 'pending'
            order.save()
            
            log_info(
                f"Order {order.id} status updated to 'pending' with payment_id {payment_id}",
                'payment_scenario_service'
            )
            
            payment_url = payment_data['confirmation']['confirmation_url']
            return HttpResponseRedirect(payment_url)
            
        except Exception as e:
            # Update order status to 'failed' on error
            order.status = 'failed'
            order.save()
            
            log_error(
                f"Failed to create Yookassa payment for Order {order.id}: {str(e)}. "
                f"Scenario: Yookassa, Merchant: {merchant.id}",
                'payment_scenario_service',
                'ERROR'
            )
            raise

    @staticmethod
    def execute_tbank_scenario(device, order, drink_details):
        """
        Executes TBank payment scenario.
        
        Args:
            device: Device instance
            order: Order instance with status='created'
            drink_details: Dict containing drink information
            
        Returns:
            HttpResponseRedirect: Redirect to TBank payment page
            
        Raises:
            ValueError: If TBank credentials are missing
        """
        merchant = device.merchant
        
        # Get TBank credentials
        credentials = PaymentScenarioService.get_merchant_credentials(
            merchant, 'TBank'
        )
        
        # Extract drink information
        drink_price = drink_details.get('price', 5000)
        drink_name = order.drink_name
        
        log_info(
            f"Processing TBank payment for Order {order.id}. "
            f"Request params: device_id={device.device_uuid}, "
            f"drink_name={drink_name}, price={drink_price}",
            'payment_scenario_service'
        )
        
        try:
            # Build success URL to order status page
            from django.conf import settings
            domain = settings.BASE_URL
            success_url = f"https://{domain}/v1/order-status-page?order_id={order.id}"
            
            # Prepare payment data for TBank
            payment_data = {
                'Amount': drink_price,
                'OrderId': str(order.id),
                'Description': f'Оплата напитка: {drink_name}',
                'SuccessURL': success_url,
            }
            
            # Process payment with merchant-specific credentials
            payment, error = t_bank_service.process_payment(
                payment_data,
                credentials
            )
            
            if error:
                raise Exception(f"TBank payment failed: {error}")
            
            # Update order with payment information and change status to 'pending'
            order.payment_reference_id = payment.payment_id
            order.status = 'pending'
            order.save()
            
            log_info(
                f"Order {order.id} status updated to 'pending' with payment_id {payment.payment_id}",
                'payment_scenario_service'
            )
            
            return HttpResponseRedirect(payment.payment_url)
            
        except Exception as e:
            # Update order status to 'failed' on error
            order.status = 'failed'
            order.save()
            
            log_error(
                f"Failed to create TBank payment for Order {order.id}: {str(e)}. "
                f"Scenario: TBank, Merchant: {merchant.id}",
                'payment_scenario_service',
                'ERROR'
            )
            raise

    @staticmethod
    def execute_custom_scenario(device, order):
        """
        Executes Custom payment scenario by redirecting to external payment system.
        
        Args:
            device: Device instance with redirect_url configured
            order: Order instance with status='created'
            
        Returns:
            HttpResponseRedirect: Redirect to custom payment URL
            
        Raises:
            ValueError: If redirect_url is not configured for the device
        """
        # Validate that redirect_url is configured
        if not device.redirect_url or device.redirect_url.strip() == '':
            error_msg = "Redirect URL not configured for custom payment scenario"
            log_error(
                f"Missing redirect_url for Device {device.device_uuid}, Order {order.id}",
                'payment_scenario_service',
                'ERROR'
            )
            raise ValueError(error_msg)
        
        log_info(
            f"Processing Custom payment for Order {order.id}. "
            f"Request params: device_id={device.device_uuid}, "
            f"redirect_url={device.redirect_url}",
            'payment_scenario_service'
        )
        
        try:
            # Build redirect URL with order parameters
            base_url = device.redirect_url
            separator = '&' if '?' in base_url else '?'
            
            redirect_url = (
                f"{base_url}{separator}"
                f"order_id={order.id}&"
                f"drink_name={order.drink_name}&"
                f"price={order.price}&"
                f"size={order.size}&"
                f"device_uuid={device.device_uuid}&"
                f"merchant_id={device.merchant.id}"
            )
            
            log_info(
                f"Redirecting Order {order.id} to custom payment URL: {redirect_url}",
                'payment_scenario_service'
            )
            
            return HttpResponseRedirect(redirect_url)
            
        except Exception as e:
            # Update order status to 'failed' on error
            order.status = 'failed'
            order.save()
            
            log_error(
                f"Failed to redirect to custom payment for Order {order.id}: {str(e)}. "
                f"Scenario: Custom, Merchant: {device.merchant.id}",
                'payment_scenario_service',
                'ERROR'
            )
            raise
