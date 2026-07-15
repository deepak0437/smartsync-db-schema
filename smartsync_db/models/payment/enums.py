"""PostgreSQL enum types for the payment schema.

Each Python enum maps 1:1 to a ``CREATE TYPE payment.<name> AS ENUM (...)``
statement in migrations.
"""

import enum


class PaymentOrderStatus(str, enum.Enum):
    """Business-level status for checkout attempts."""

    PENDING = "PENDING"
    CREATED = "CREATED"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentGateway(str, enum.Enum):
    """Supported payment gateways."""

    RAZORPAY = "RAZORPAY"
    STRIPE = "STRIPE"
    CASHFREE = "CASHFREE"


class PaymentMethod(str, enum.Enum):
    """Payment channels verified by the gateway."""

    CARD = "CARD"
    UPI = "UPI"
    NETBANKING = "NETBANKING"
    WALLET = "WALLET"
    EMI = "EMI"
    OTHER = "OTHER"


class PaymentStatus(str, enum.Enum):
    """Gateway payment attempt status."""

    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"


class TransactionType(str, enum.Enum):
    """Money ledger transaction type."""

    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    CHARGEBACK = "CHARGEBACK"
    ADJUSTMENT = "ADJUSTMENT"


class TransactionStatus(str, enum.Enum):
    """Ledger transaction status."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class InvoiceStatus(str, enum.Enum):
    """Billing invoice status."""

    ISSUED = "ISSUED"
    VOID = "VOID"


class RefundStatus(str, enum.Enum):
    """Refund lifecycle status."""

    REQUESTED = "REQUESTED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
