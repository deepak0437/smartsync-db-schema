"""initial_payment_schema

Revision ID: 01
Revises: None
Create Date: 2026-07-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum types are created implicitly by the first `sa.Enum(...)` column that
    # references them below (checkfirst=True), same as schemas/platform's migration —
    # no separate CREATE TYPE step, so enum values have a single source of truth.

    # Create payment_orders table
    op.create_table('payment_orders',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('mobile_number', sa.String(length=20), nullable=False),
        sa.Column('school_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('plan_id', sa.BigInteger(), nullable=False),
        sa.Column('addon_id', sa.BigInteger(), nullable=True),
        sa.Column('subtotal_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('gateway_order_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'CREATED', 'PAID', 'FAILED', 'CANCELLED', name='payment_order_status', schema='payment'), server_default='PENDING', nullable=False),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('updated_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), server_default=sa.text('EXTRACT(EPOCH FROM NOW())::BIGINT'), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), server_default=sa.text('EXTRACT(EPOCH FROM NOW())::BIGINT'), nullable=False),
        sa.CheckConstraint('subtotal_amount >= 0', name='chk_payment_orders_subtotal'),
        sa.CheckConstraint('discount_amount >= 0', name='chk_payment_orders_discount'),
        sa.CheckConstraint('tax_amount >= 0', name='chk_payment_orders_tax'),
        sa.CheckConstraint('total_amount >= 0', name='chk_payment_orders_total'),
        sa.PrimaryKeyConstraint('id'),
        schema='payment'
    )
    op.create_index('ix_payment_orders_mobile_number', 'payment_orders', ['mobile_number'], unique=False, schema='payment')
    op.create_index('ix_payment_orders_plan_id', 'payment_orders', ['plan_id'], unique=False, schema='payment')
    op.create_index('uq_payment_orders_gateway_order_id', 'payment_orders', ['gateway_order_id'], unique=True, schema='payment', postgresql_where=sa.text('gateway_order_id IS NOT NULL'))
    op.create_index('ix_payment_orders_status_created_at', 'payment_orders', ['status', 'created_at'], unique=False, schema='payment')

    # Create payments table
    op.create_table('payments',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('payment_order_id', sa.BigInteger(), nullable=False),
        sa.Column('gateway', sa.Enum('RAZORPAY', 'STRIPE', 'CASHFREE', name='payment_gateway', schema='payment'), nullable=False),
        sa.Column('gateway_payment_id', sa.String(length=255), nullable=True),
        sa.Column('transaction_reference', sa.String(length=255), nullable=True),
        sa.Column('payment_method', sa.Enum('CARD', 'UPI', 'NETBANKING', 'WALLET', 'EMI', 'OTHER', name='payment_method', schema='payment'), nullable=True),
        sa.Column('payment_status', sa.Enum('INITIATED', 'SUCCESS', 'FAILED', 'PENDING', 'REFUNDED', 'PARTIALLY_REFUNDED', name='payment_status', schema='payment'), server_default='INITIATED', nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='INR', nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('gateway_fee', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('tax_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('failure_reason', sa.Text(), nullable=True),
        sa.Column('verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('gateway_response', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('updated_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), server_default=sa.text('EXTRACT(EPOCH FROM NOW())::BIGINT'), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), server_default=sa.text('EXTRACT(EPOCH FROM NOW())::BIGINT'), nullable=False),
        sa.CheckConstraint('amount >= 0', name='chk_payments_amount_non_negative'),
        sa.CheckConstraint('gateway_fee IS NULL OR gateway_fee >= 0', name='chk_payments_gateway_fee_non_negative'),
        sa.CheckConstraint('tax_amount IS NULL OR tax_amount >= 0', name='chk_payments_tax_amount_non_negative'),
        sa.ForeignKeyConstraint(['payment_order_id'], ['payment.payment_orders.id'], name='fk_payments_payment_order_id'),
        sa.PrimaryKeyConstraint('id'),
        schema='payment'
    )
    op.create_index('ix_payments_payment_order_id', 'payments', ['payment_order_id'], unique=False, schema='payment')
    op.create_index('uq_payments_gateway_payment_id', 'payments', ['gateway_payment_id'], unique=True, schema='payment', postgresql_where=sa.text('gateway_payment_id IS NOT NULL'))
    op.create_index('ix_payments_payment_status', 'payments', ['payment_status'], unique=False, schema='payment')
    op.create_index('ix_payments_paid_at', 'payments', ['paid_at'], unique=False, schema='payment')

    # Create payment_transactions table
    op.create_table('payment_transactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('payment_id', sa.BigInteger(), nullable=False),
        sa.Column('transaction_type', sa.Enum('PAYMENT', 'REFUND', 'CHARGEBACK', 'ADJUSTMENT', name='transaction_type', schema='payment'), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'SUCCESS', 'FAILED', name='transaction_status', schema='payment'), nullable=False),
        sa.Column('gateway_transaction_id', sa.String(length=255), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('updated_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), server_default=sa.text('EXTRACT(EPOCH FROM NOW())::BIGINT'), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), server_default=sa.text('EXTRACT(EPOCH FROM NOW())::BIGINT'), nullable=False),
        sa.CheckConstraint('amount >= 0', name='chk_payment_transactions_amount_non_negative'),
        sa.ForeignKeyConstraint(['payment_id'], ['payment.payments.id'], name='fk_payment_transactions_payment_id'),
        sa.PrimaryKeyConstraint('id'),
        schema='payment'
    )
    op.create_index('ix_payment_transactions_payment_id', 'payment_transactions', ['payment_id'], unique=False, schema='payment')
    op.create_index('ix_payment_transactions_type', 'payment_transactions', ['transaction_type'], unique=False, schema='payment')
    op.create_index('ix_payment_transactions_gateway_transaction_id', 'payment_transactions', ['gateway_transaction_id'], unique=False, schema='payment')

    # Create invoices table
    op.create_table('invoices',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('payment_id', sa.BigInteger(), nullable=False),
        sa.Column('school_id', sa.BigInteger(), nullable=True),
        sa.Column('billing_name', sa.String(length=255), nullable=False),
        sa.Column('billing_email', sa.String(length=255), nullable=True),
        sa.Column('billing_address', sa.Text(), nullable=True),
        sa.Column('gst_number', sa.String(length=20), nullable=True),
        sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('discount', sa.Numeric(precision=10, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('tax', sa.Numeric(precision=10, scale=2), server_default=sa.text('0.00'), nullable=False),
        sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('invoice_url', sa.String(length=500), nullable=True),
        sa.Column('status', sa.Enum('ISSUED', 'VOID', name='invoice_status', schema='payment'), server_default='ISSUED', nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('updated_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), server_default=sa.text('EXTRACT(EPOCH FROM NOW())::BIGINT'), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), server_default=sa.text('EXTRACT(EPOCH FROM NOW())::BIGINT'), nullable=False),
        sa.CheckConstraint('subtotal >= 0', name='chk_invoices_subtotal_non_negative'),
        sa.CheckConstraint('discount >= 0', name='chk_invoices_discount_non_negative'),
        sa.CheckConstraint('tax >= 0', name='chk_invoices_tax_non_negative'),
        sa.CheckConstraint('total >= 0', name='chk_invoices_total_non_negative'),
        sa.ForeignKeyConstraint(['payment_id'], ['payment.payments.id'], name='fk_invoices_payment_id'),
        sa.PrimaryKeyConstraint('id'),
        schema='payment'
    )
    op.create_index('uq_invoices_invoice_number', 'invoices', ['invoice_number'], unique=True, schema='payment')
    op.create_index('uq_invoices_payment_id', 'invoices', ['payment_id'], unique=True, schema='payment')
    op.create_index('ix_invoices_school_id', 'invoices', ['school_id'], unique=False, schema='payment')

    # Create refunds table
    op.create_table('refunds',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('payment_id', sa.BigInteger(), nullable=False),
        sa.Column('gateway_refund_id', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('REQUESTED', 'PROCESSING', 'PROCESSED', 'FAILED', name='refund_status', schema='payment'), server_default='REQUESTED', nullable=False),
        sa.Column('requested_by', sa.BigInteger(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('updated_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), server_default=sa.text('EXTRACT(EPOCH FROM NOW())::BIGINT'), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), server_default=sa.text('EXTRACT(EPOCH FROM NOW())::BIGINT'), nullable=False),
        sa.CheckConstraint('amount >= 0', name='chk_refunds_amount_non_negative'),
        sa.ForeignKeyConstraint(['payment_id'], ['payment.payments.id'], name='fk_refunds_payment_id'),
        sa.PrimaryKeyConstraint('id'),
        schema='payment'
    )
    op.create_index('ix_refunds_payment_id', 'refunds', ['payment_id'], unique=False, schema='payment')
    op.create_index('uq_refunds_gateway_refund_id', 'refunds', ['gateway_refund_id'], unique=True, schema='payment', postgresql_where=sa.text('gateway_refund_id IS NOT NULL'))
    op.create_index('ix_refunds_status', 'refunds', ['status'], unique=False, schema='payment')

    # Create payment_webhooks table
    op.create_table('payment_webhooks',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('gateway', sa.Enum('RAZORPAY', 'STRIPE', 'CASHFREE', name='payment_gateway', schema='payment'), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('payload', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('signature', sa.String(length=500), nullable=True),
        sa.Column('processed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column('updated_by', sa.BigInteger(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), server_default=sa.text('EXTRACT(EPOCH FROM NOW())::BIGINT'), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), server_default=sa.text('EXTRACT(EPOCH FROM NOW())::BIGINT'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='payment'
    )
    op.create_index('uq_payment_webhooks_gateway_event_id', 'payment_webhooks', ['gateway', 'event_id'], unique=True, schema='payment')
    op.create_index('ix_payment_webhooks_event_type', 'payment_webhooks', ['event_type'], unique=False, schema='payment')


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table('payment_webhooks', schema='payment')
    op.drop_table('refunds', schema='payment')
    op.drop_table('invoices', schema='payment')
    op.drop_table('payment_transactions', schema='payment')
    op.drop_table('payments', schema='payment')
    op.drop_table('payment_orders', schema='payment')

    # Drop enums
    op.execute(sa.text("DROP TYPE payment.refund_status"))
    op.execute(sa.text("DROP TYPE payment.invoice_status"))
    op.execute(sa.text("DROP TYPE payment.transaction_status"))
    op.execute(sa.text("DROP TYPE payment.transaction_type"))
    op.execute(sa.text("DROP TYPE payment.payment_status"))
    op.execute(sa.text("DROP TYPE payment.payment_method"))
    op.execute(sa.text("DROP TYPE payment.payment_gateway"))
    op.execute(sa.text("DROP TYPE payment.payment_order_status"))
