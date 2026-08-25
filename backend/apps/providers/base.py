from abc import ABC, abstractmethod

class PaymentProvider(ABC):
    """
    Abstract Interface for Imara Pay Payment Providers.
    All integrations (M-Pesa Daraja, Sandbox, PSPs) implement this contract.
    """
    @abstractmethod
    def initiate_payment(self, payment_attempt):
        """
        Initiates the payment (e.g. STK Push).
        Returns dict with status and external_reference.
        """
        pass

    @abstractmethod
    def query_payment(self, payment_attempt):
        """
        Queries provider for status of a payment attempt.
        """
        pass

    @abstractmethod
    def handle_webhook(self, payload, headers=None):
        """
        Processes provider webhook event.
        """
        pass
