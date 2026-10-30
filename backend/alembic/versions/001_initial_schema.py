"""001_initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-30 20:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Stores
    op.create_table(
        'stores',
        sa.Column('store_id', sa.String(), nullable=False),
        sa.Column('store_name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='INR'),
        sa.Column('timezone', sa.String(), nullable=False, server_default='Asia/Kolkata'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('store_id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_stores_slug'), 'stores', ['slug'], unique=True)
    op.create_index(op.f('ix_stores_store_id'), 'stores', ['store_id'], unique=False)

    # 2. Customers
    op.create_table(
        'customers',
        sa.Column('customer_id', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('customer_id')
    )
    op.create_index(op.f('ix_customers_customer_id'), 'customers', ['customer_id'], unique=False)

    # 3. Products
    op.create_table(
        'products',
        sa.Column('product_id', sa.String(), nullable=False),
        sa.Column('store_id', sa.String(), nullable=False),
        sa.Column('sku', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('brand', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('sale_unit', sa.String(), nullable=False),
        sa.Column('pack_size', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('pack_size_unit', sa.String(), nullable=False),
        sa.Column('price_inr', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.CheckConstraint('price_inr >= 0', name='chk_positive_price'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.store_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id'),
        sa.UniqueConstraint('store_id', 'sku', name='uq_store_sku')
    )
    op.create_index(op.f('ix_products_brand'), 'products', ['brand'], unique=False)
    op.create_index(op.f('ix_products_category'), 'products', ['category'], unique=False)
    op.create_index(op.f('ix_products_is_active'), 'products', ['is_active'], unique=False)
    op.create_index(op.f('ix_products_name'), 'products', ['name'], unique=False)
    op.create_index(op.f('ix_products_product_id'), 'products', ['product_id'], unique=False)
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=False)
    op.create_index(op.f('ix_products_store_id'), 'products', ['store_id'], unique=False)

    # 4. Product Aliases
    op.create_table(
        'product_aliases',
        sa.Column('alias_id', sa.String(), nullable=False),
        sa.Column('product_id', sa.String(), nullable=False),
        sa.Column('alias', sa.String(), nullable=False),
        sa.Column('normalized_alias', sa.String(), nullable=False),
        sa.Column('language', sa.String(), nullable=False),
        sa.Column('alias_type', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.product_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('alias_id')
    )
    op.create_index('idx_alias_normalized', 'product_aliases', ['normalized_alias'], unique=False)
    op.create_index(op.f('ix_product_aliases_alias_id'), 'product_aliases', ['alias_id'], unique=False)
    op.create_index(op.f('ix_product_aliases_product_id'), 'product_aliases', ['product_id'], unique=False)

    # 5. Inventory
    op.create_table(
        'inventory',
        sa.Column('product_id', sa.String(), nullable=False),
        sa.Column('stock_quantity', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('stock_unit', sa.String(), nullable=False),
        sa.Column('low_stock_threshold', sa.Numeric(precision=12, scale=3), nullable=False, server_default='0'),
        sa.Column('reserved_quantity', sa.Numeric(precision=12, scale=3), nullable=False, server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('stock_quantity >= 0', name='chk_non_negative_stock'),
        sa.CheckConstraint('reserved_quantity >= 0', name='chk_non_negative_reserved'),
        sa.ForeignKeyConstraint(['product_id'], ['products.product_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id')
    )

    # 6. Order Sessions
    op.create_table(
        'order_sessions',
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('store_id', sa.String(), nullable=False),
        sa.Column('customer_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='active'),
        sa.Column('current_cart', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('active', 'confirmed', 'expired')", name='chk_session_status'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.store_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('session_id')
    )
    op.create_index(op.f('ix_order_sessions_session_id'), 'order_sessions', ['session_id'], unique=False)
    op.create_index(op.f('ix_order_sessions_store_id'), 'order_sessions', ['store_id'], unique=False)

    # 7. Orders
    op.create_table(
        'orders',
        sa.Column('order_id', sa.String(), nullable=False),
        sa.Column('store_id', sa.String(), nullable=False),
        sa.Column('session_id', sa.String(), nullable=True),
        sa.Column('customer_id', sa.String(), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('total_amount >= 0', name='chk_positive_order_total'),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'preparing', 'ready', 'completed', 'rejected', 'cancelled')", name='chk_order_status'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['order_sessions.session_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['store_id'], ['stores.store_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('order_id')
    )
    op.create_index(op.f('ix_orders_order_id'), 'orders', ['order_id'], unique=False)
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'], unique=False)
    op.create_index(op.f('ix_orders_store_id'), 'orders', ['store_id'], unique=False)

    # 8. Order Items
    op.create_table(
        'order_items',
        sa.Column('item_id', sa.String(), nullable=False),
        sa.Column('order_id', sa.String(), nullable=False),
        sa.Column('product_id', sa.String(), nullable=False),
        sa.Column('product_name_snapshot', sa.String(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('unit', sa.String(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.CheckConstraint('quantity > 0', name='chk_positive_quantity'),
        sa.CheckConstraint('unit_price >= 0', name='chk_positive_unit_price'),
        sa.CheckConstraint('subtotal >= 0', name='chk_positive_subtotal'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.order_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.product_id']),
        sa.PrimaryKeyConstraint('item_id')
    )
    op.create_index(op.f('ix_order_items_item_id'), 'order_items', ['item_id'], unique=False)
    op.create_index(op.f('ix_order_items_order_id'), 'order_items', ['order_id'], unique=False)
    op.create_index(op.f('ix_order_items_product_id'), 'order_items', ['product_id'], unique=False)

    # 9. Stock Movements
    op.create_table(
        'stock_movements',
        sa.Column('movement_id', sa.String(), nullable=False),
        sa.Column('product_id', sa.String(), nullable=False),
        sa.Column('order_id', sa.String(), nullable=True),
        sa.Column('change_quantity', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.order_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.product_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('movement_id')
    )
    op.create_index(op.f('ix_stock_movements_movement_id'), 'stock_movements', ['movement_id'], unique=False)
    op.create_index(op.f('ix_stock_movements_order_id'), 'stock_movements', ['order_id'], unique=False)
    op.create_index(op.f('ix_stock_movements_product_id'), 'stock_movements', ['product_id'], unique=False)


def downgrade() -> None:
    op.drop_table('stock_movements')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('order_sessions')
    op.drop_table('inventory')
    op.drop_table('product_aliases')
    op.drop_table('products')
    op.drop_table('customers')
    op.drop_table('stores')
