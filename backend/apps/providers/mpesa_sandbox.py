import uuid
import random
import string
import hashlib
from django.utils import timezone
from apps.providers.base import PaymentProvider
from apps.payments.models import Transaction, PaymentRequest
from apps.webhooks.models import WebhookEvent
from apps.whatsapp.adapter import WhatsAppBusinessAdapter

class MPesaSandboxAdapter(PaymentProvider):
    """
    Safaricom M-Pesa STK Push Sandbox Adapter.
    Simulates real M-Pesa Daraja Express STK Push initiation & callbacks.
    """

    def initiate_payment(self, payment_attempt):
        checkout_req_id = f"ws_CO_{timezone.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
        merchant_req_id = f"{random.randint(10000, 99999)}-{random.randint(1000, 9999)}-1"

        payment_attempt.external_reference = checkout_req_id
        payment_attempt.status = 'PENDING'
        payment_attempt.raw_response = {
            'MerchantRequestID': merchant_req_id,
            'CheckoutRequestID': checkout_req_id,
            'ResponseCode': '0',
            'ResponseDescription': 'Success. Request accepted for processing',
            'CustomerMessage': f'Success. Request accepted for processing. Check your phone ({payment_attempt.customer_phone}) to enter PIN.'
        }
        payment_attempt.save()

        # Update PaymentRequest status to PENDING
        req = payment_attempt.payment_request
        if req.status == 'CREATED':
            req.status = 'PENDING'
            req.save()

        return {
            'success': True,
            'checkout_request_id': checkout_req_id,
            'merchant_request_id': merchant_req_id,
            'message': 'STK Push sent to customer phone.'
        }

    def query_payment(self, payment_attempt):
        return {
            'checkout_request_id': payment_attempt.external_reference,
            'status': payment_attempt.status,
            'is_complete': payment_attempt.status in ['SUCCESS', 'FAILED', 'TIMEOUT']
        }

    def process_callback(self, checkout_request_id, result_code=0, result_desc="The service request is processed successfully.", mpesa_receipt=None):
        """
        Internal simulator method to process Safaricom M-Pesa callback payload.
        """
        from apps.payments.models import PaymentAttempt

        attempt = PaymentAttempt.objects.filter(external_reference=checkout_request_id).first()
        if not attempt:
            return {'success': False, 'error': 'Payment attempt not found'}

        req = attempt.payment_request

        # Idempotency check: if already processed, return idempotently
        if attempt.status in ['SUCCESS', 'FAILED']:
            return {
                'success': True,
                'already_processed': True,
                'status': attempt.status
            }

        # Format Safaricom M-Pesa receipt code
        if not mpesa_receipt and result_code == 0:
            date_prefix = "".join(random.choices(string.ascii_uppercase, k=3))
            num_suffix = "".join(random.choices(string.digits, k=7))
            mpesa_receipt = f"{date_prefix}{num_suffix}"

        # External event ID for webhook idempotency
        event_id = f"mpesa_stk_{checkout_request_id}_{result_code}"
        payload_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": attempt.raw_response.get('MerchantRequestID', '1234'),
                    "CheckoutRequestID": checkout_request_id,
                    "ResultCode": result_code,
                    "ResultDesc": result_desc,
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": req.amount_minor},
                            {"Name": "MpesaReceiptNumber", "Value": mpesa_receipt},
                            {"Name": "TransactionDate", "Value": int(timezone.now().timestamp())},
                            {"Name": "PhoneNumber", "Value": attempt.customer_phone}
                        ]
                    } if result_code == 0 else []
                }
            }
        }

        payload_hash = hashlib.sha256(str(payload_data).encode('utf-8')).hexdigest()

        webhook_event, created = WebhookEvent.objects.get_or_create(
            provider='MPESA_SANDBOX',
            external_event_id=event_id,
            defaults={
                'payload_hash': payload_hash,
                'payload': payload_data,
                'processing_status': 'PENDING'
            }
        )

        if not created and webhook_event.processing_status == 'PROCESSED':
            return {'success': True, 'duplicate': True}

        if result_code == 0:
            attempt.status = 'SUCCESS'
            attempt.raw_response['callback'] = payload_data
            attempt.save()

            req.status = 'SUCCEEDED'
            req.paid_at = timezone.now()
            req.customer_phone = attempt.customer_phone
            req.save()

            # Create immutable Transaction record
            tx, tx_created = Transaction.objects.get_or_create(
                mpesa_receipt_number=mpesa_receipt,
                defaults={
                    'tenant': req.tenant,
                    'payment_request': req,
                    'payment_attempt': attempt,
                    'amount_minor': req.amount_minor,
                    'currency': req.currency,
                    'customer_phone': attempt.customer_phone,
                    'status': 'SUCCEEDED',
                    'paid_at': req.paid_at
                }
            )

            webhook_event.processing_status = 'PROCESSED'
            webhook_event.processed_at = timezone.now()
            webhook_event.save()

            # Trigger async WhatsApp receipt notification simulation
            wa_adapter = WhatsAppBusinessAdapter()
            wa_adapter.send_payment_receipt_notification(req, mpesa_receipt)

            return {
                'success': True,
                'status': 'SUCCEEDED',
                'mpesa_receipt': mpesa_receipt,
                'transaction_id': str(tx.id)
            }
        else:
            attempt.status = 'FAILED'
            attempt.raw_response['callback'] = payload_data
            attempt.save()

            req.status = 'FAILED'
            req.save()

            webhook_event.processing_status = 'PROCESSED'
            webhook_event.processed_at = timezone.now()
            webhook_event.error_message = result_desc
            webhook_event.save()

            return {
                'success': True,
                'status': 'FAILED',
                'reason': result_desc
            }

    def handle_webhook(self, payload, headers=None):
        body = payload.get('Body', {}).get('stkCallback', {})
        checkout_req_id = body.get('CheckoutRequestID')
        result_code = body.get('ResultCode', 1)
        result_desc = body.get('ResultDesc', 'Failed')

        items = body.get('CallbackMetadata', {}).get('Item', [])
        mpesa_receipt = None
        for item in items:
            if item.get('Name') == 'MpesaReceiptNumber':
                mpesa_receipt = item.get('Value')

        return self.process_callback(checkout_req_id, result_code, result_desc, mpesa_receipt)
