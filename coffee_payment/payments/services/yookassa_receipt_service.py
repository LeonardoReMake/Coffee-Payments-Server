from yookassa import Configuration, Payment
from payments.models import Receipt, Order
from payments.utils.logging import log_info, log_error


class YookassaReceiptService:
    """
    Service for creating Yookassa payments with fiscal receipts.
    Extends base Yookassa functionality with receipt generation.
    """
    
    @staticmethod
    def create_payment_with_receipt(
        amount, description, return_url, drink_no, order_uuid, size,
        credentials, email=None, drink_meta=None, drink_name=None
    ):
        """
        Creates a Yookassa payment with optional receipt.
        
        Args:
            amount: Payment amount in rubles
            description: Payment description
            return_url: URL to redirect after payment
            drink_no: Drink number/ID
            order_uuid: Order UUID
            size: Drink size
            credentials: Merchant credentials including receipt settings
            email: Customer email (optional)
            drink_meta: Drink metadata for receipt (optional)
            drink_name: Name of the drink (optional)
            
        Returns:
            Payment object from Yookassa API
        """
        # Configure Yookassa with merchant credentials
        account_id = credentials['account_id']
        secret_key = credentials['secret_key']
        
        Configuration.account_id = account_id
        Configuration.secret_key = secret_key
        
        # Build payment request
        payment_data = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "description": description,
            "metadata": {
                "order_uuid": str(order_uuid),
                "drink_number": str(drink_no),
                "size": str(size)
            }
        }
        
        # Add receipt if email provided
        if email:
            receipt = YookassaReceiptService.build_receipt_object(
                email=email,
                drink_name=drink_name or description,
                amount=amount,
                credentials=credentials,
                drink_meta=drink_meta
            )
            payment_data['receipt'] = receipt
            
            log_info(
                f"Creating Yookassa payment with receipt for order {order_uuid}. "
                f"Email: {email[:3]}***@***, has_drink_meta: {bool(drink_meta)}",
                'yookassa_receipt_service'
            )
        else:
            log_info(
                f"Creating Yookassa payment without receipt for order {order_uuid}",
                'yookassa_receipt_service'
            )
        
        # Create payment
        payment = Payment.create(payment_data)
        
        return payment
    
    @staticmethod
    def build_receipt_object(email, drink_name, amount, credentials, drink_meta=None):
        """
        Builds receipt object for Yookassa API.
        
        Implements fallback logic:
        1. Try to get field from drink_meta
        2. If not found, try to get from credentials
        3. If not found in either, exclude field
        
        Args:
            email: Customer email
            drink_name: Name of the drink
            amount: Payment amount in rubles
            credentials: Merchant credentials
            drink_meta: Drink metadata (optional)
            
        Returns:
            dict: Receipt object for Yookassa API
        """
        def get_field_with_fallback(field_name):
            """Helper to get field with fallback logic"""
            if drink_meta and field_name in drink_meta:
                log_info(
                    f"Using drink_meta value for field '{field_name}'",
                    'yookassa_receipt_service'
                )
                return drink_meta[field_name]
            if field_name in credentials:
                log_info(
                    f"Using credential fallback for field '{field_name}'",
                    'yookassa_receipt_service'
                )
                return credentials[field_name]
            return None
        
        # Build receipt object
        receipt = {
            "customer": {
                "email": email
            },
            "items": [{
                "description": drink_name,
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "quantity": 1
            }],
            "internet": False
        }
        
        # Add optional item fields with fallback
        item = receipt["items"][0]
        
        vat_code = get_field_with_fallback('vat_code')
        if vat_code is not None:
            item['vat_code'] = vat_code
        
        measure = get_field_with_fallback('measure')
        if measure is not None:
            item['measure'] = measure
        
        payment_subject = get_field_with_fallback('payment_subject')
        if payment_subject is not None:
            item['payment_subject'] = payment_subject
        
        payment_mode = get_field_with_fallback('payment_mode')
        if payment_mode is not None:
            item['payment_mode'] = payment_mode
        
        # Add receipt-level fields from credentials
        if 'tax_system_code' in credentials:
            receipt['tax_system_code'] = credentials['tax_system_code']
        
        if 'timezone' in credentials:
            receipt['timezone'] = credentials['timezone']
        
        log_info(
            f"Built receipt object with email: {email[:3]}***@***",
            'yookassa_receipt_service'
        )
        
        return receipt
    
    @staticmethod
    def save_receipt_record(order, email, receipt_data):
        """
        Saves receipt record to database.
        
        Args:
            order: Order instance
            email: Customer email
            receipt_data: Complete receipt data sent to Yookassa
            
        Returns:
            Receipt: Created receipt instance
        """
        try:
            receipt = Receipt.objects.create(
                order=order,
                contact=email,
                drink_no=order.drink_number,
                amount=order.price,
                receipt_data=receipt_data,
                status='pending'
            )
            
            log_info(
                f"Receipt created for Order {order.id}. "
                f"Receipt ID: {receipt.id}, Amount: {receipt.amount}",
                'yookassa_receipt_service'
            )
            
            return receipt
            
        except Exception as e:
            log_error(
                f"Failed to save receipt record for Order {order.id}: {str(e)}",
                'yookassa_receipt_service',
                'ERROR'
            )
            raise
