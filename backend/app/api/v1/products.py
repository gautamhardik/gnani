import uuid
from typing import Any, Dict, List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func

from backend.app.api.deps import get_db, get_current_merchant
from backend.app.core.config import settings
from backend.app.models import Product, ProductAlias, StoreInventory, Store
from backend.app.schemas import (
    ProductResponse,
    ProductCreate,
    ProductUpdate,
    ProductSearchResult,
    PaginatedResponse,
    MessageResponse,
    InventoryResponse,
)

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("", response_model=PaginatedResponse[ProductResponse])
def list_products(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    store_id: str = settings.DEMO_STORE_ID,
    db: Session = Depends(get_db)
):
    """Lists products with optional filtering by category and active status."""
    query = (
        db.query(Product)
        .options(joinedload(Product.inventory), joinedload(Product.aliases))
        .filter(Product.store_id == store_id)
    )

    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)

    total = query.count()
    offset = (page - 1) * size
    products = query.order_by(Product.product_id).offset(offset).limit(size).all()

    items = []
    for p in products:
        inv_resp = None
        if p.inventory:
            inv_resp = InventoryResponse(
                product_id=p.inventory.product_id,
                stock_quantity=p.inventory.stock_quantity,
                stock_unit=p.inventory.stock_unit,
                low_stock_threshold=p.inventory.low_stock_threshold,
                reserved_quantity=p.inventory.reserved_quantity,
                is_low_stock=p.inventory.stock_quantity <= p.inventory.low_stock_threshold,
                is_out_of_stock=p.inventory.stock_quantity == 0,
                updated_at=p.inventory.updated_at
            )
        items.append(
            ProductResponse(
                product_id=p.product_id,
                store_id=p.store_id,
                sku=p.sku,
                name=p.name,
                brand=p.brand,
                category=p.category,
                sale_unit=p.sale_unit,
                pack_size=p.pack_size,
                pack_size_unit=p.pack_size_unit,
                price_inr=p.price_inr,
                is_active=p.is_active,
                description=p.description,
                inventory=inv_resp,
                aliases=p.aliases or []
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        has_more=(offset + len(items)) < total
    )


@router.get("/search", response_model=List[ProductSearchResult])
def search_products(
    q: str = Query(..., min_length=1, description="Search query in English, Hindi, or Hinglish"),
    limit: int = Query(15, ge=1, le=50),
    store_id: str = settings.DEMO_STORE_ID,
    db: Session = Depends(get_db)
):
    """
    Searches catalogue by canonical name, brand, or colloquial product aliases.
    Preserves alias match context for dialogue explanation.
    """
    clean_q = q.strip().lower()

    # 1. Search canonical product name and brand
    canonical_matches = (
        db.query(Product)
        .options(joinedload(Product.inventory))
        .filter(
            Product.store_id == store_id,
            Product.is_active == True,
            or_(
                Product.name.ilike(f"%{clean_q}%"),
                Product.brand.ilike(f"%{clean_q}%"),
                Product.category.ilike(f"%{clean_q}%")
            )
        )
        .limit(limit)
        .all()
    )

    results = []
    seen_ids = set()

    for p in canonical_matches:
        seen_ids.add(p.product_id)
        stock = p.inventory.stock_quantity if p.inventory else Decimal(0)
        source = "brand" if p.brand and clean_q in p.brand.lower() else "canonical"
        results.append(
            ProductSearchResult(
                product_id=p.product_id,
                name=p.name,
                brand=p.brand,
                category=p.category,
                sale_unit=p.sale_unit,
                pack_size=p.pack_size,
                pack_size_unit=p.pack_size_unit,
                price_inr=p.price_inr,
                is_active=p.is_active,
                stock_quantity=stock,
                matched_alias=None,
                match_source=source
            )
        )

    # 2. Search aliases if more room
    if len(results) < limit:
        alias_matches = (
            db.query(ProductAlias, Product)
            .join(Product, ProductAlias.product_id == Product.product_id)
            .options(joinedload(Product.inventory))
            .filter(
                Product.store_id == store_id,
                Product.is_active == True,
                or_(
                    ProductAlias.normalized_alias.ilike(f"%{clean_q}%"),
                    ProductAlias.alias.ilike(f"%{clean_q}%")
                )
            )
            .limit(limit - len(results))
            .all()
        )

        for alias_obj, p in alias_matches:
            if p.product_id not in seen_ids:
                seen_ids.add(p.product_id)
                stock = p.inventory.stock_quantity if p.inventory else Decimal(0)
                results.append(
                    ProductSearchResult(
                        product_id=p.product_id,
                        name=p.name,
                        brand=p.brand,
                        category=p.category,
                        sale_unit=p.sale_unit,
                        pack_size=p.pack_size,
                        pack_size_unit=p.pack_size_unit,
                        price_inr=p.price_inr,
                        is_active=p.is_active,
                        stock_quantity=stock,
                        matched_alias=alias_obj.alias,
                        match_source="alias"
                    )
                )

    return results


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: str,
    db: Session = Depends(get_db)
):
    """Retrieves authoritative product details, current stock, and alias mappings."""
    p = (
        db.query(Product)
        .options(joinedload(Product.inventory), joinedload(Product.aliases))
        .filter(Product.product_id == product_id)
        .first()
    )
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found"
        )

    inv_resp = None
    if p.inventory:
        inv_resp = InventoryResponse(
            product_id=p.inventory.product_id,
            stock_quantity=p.inventory.stock_quantity,
            stock_unit=p.inventory.stock_unit,
            low_stock_threshold=p.inventory.low_stock_threshold,
            reserved_quantity=p.inventory.reserved_quantity,
            is_low_stock=p.inventory.stock_quantity <= p.inventory.low_stock_threshold,
            is_out_of_stock=p.inventory.stock_quantity == 0,
            updated_at=p.inventory.updated_at
        )

    return ProductResponse(
        product_id=p.product_id,
        store_id=p.store_id,
        sku=p.sku,
        name=p.name,
        brand=p.brand,
        category=p.category,
        sale_unit=p.sale_unit,
        pack_size=p.pack_size,
        pack_size_unit=p.pack_size_unit,
        price_inr=p.price_inr,
        is_active=p.is_active,
        description=p.description,
        inventory=inv_resp,
        aliases=p.aliases or []
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    db: Session = Depends(get_db),
    current_merchant: Dict[str, Any] = Depends(get_current_merchant)
):
    """Creates a new catalogue product and initializes its inventory (Merchant Protected)."""
    target_store_id = product_in.store_id or settings.DEMO_STORE_ID
    merchant_store = current_merchant.get("store_id")
    if merchant_store and merchant_store != target_store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized: Cannot create products for store '{target_store_id}'"
        )

    store = db.query(Store).filter(Store.store_id == target_store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Store with ID '{target_store_id}' does not exist"
        )

    # Check unique sku per store
    existing_sku = db.query(Product).filter(
        Product.store_id == target_store_id,
        Product.sku == product_in.sku
    ).first()
    if existing_sku:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Product with SKU '{product_in.sku}' already exists in store '{target_store_id}'"
        )

    # Generate product_id if not given
    prod_id = product_in.product_id or f"PRD{uuid.uuid4().hex[:6].upper()}"

    new_prod = Product(
        product_id=prod_id,
        store_id=target_store_id,
        sku=product_in.sku,
        name=product_in.name,
        brand=product_in.brand,
        category=product_in.category,
        sale_unit=product_in.sale_unit,
        pack_size=product_in.pack_size,
        pack_size_unit=product_in.pack_size_unit,
        price_inr=product_in.price_inr,
        is_active=product_in.is_active,
        description=product_in.description
    )
    db.add(new_prod)
    db.flush()

    # Initialize inventory record
    new_inv = StoreInventory(
        product_id=prod_id,
        stock_quantity=product_in.initial_stock,
        stock_unit=product_in.sale_unit,
        low_stock_threshold=product_in.low_stock_threshold,
        reserved_quantity=Decimal(0)
    )
    db.add(new_inv)

    # Add any aliases
    if product_in.aliases:
        for a_text in product_in.aliases:
            if a_text.strip():
                new_alias = ProductAlias(
                    alias_id=f"ALS{uuid.uuid4().hex[:8].upper()}",
                    product_id=prod_id,
                    alias=a_text.strip(),
                    normalized_alias=a_text.strip().lower(),
                    language="hi-Latn",
                    alias_type="colloquial"
                )
                db.add(new_alias)

    db.commit()
    db.refresh(new_prod)
    return get_product(prod_id, db)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    update_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_merchant: Dict[str, Any] = Depends(get_current_merchant)
):
    """Updates product attributes and prices (Merchant Protected)."""
    p = db.query(Product).filter(Product.product_id == product_id).first()
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found"
        )

    merchant_store = current_merchant.get("store_id")
    if merchant_store and merchant_store != p.store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized: Cannot update product for store '{p.store_id}'"
        )

    for field, val in update_data.model_dump(exclude_unset=True).items():
        setattr(p, field, val)

    db.commit()
    db.refresh(p)
    return get_product(product_id, db)


@router.delete("/{product_id}", response_model=MessageResponse)
def deactivate_product(
    product_id: str,
    db: Session = Depends(get_db),
    current_merchant: Dict[str, Any] = Depends(get_current_merchant)
):
    """Soft-deactivates product from customer ordering (Merchant Protected)."""
    p = db.query(Product).filter(Product.product_id == product_id).first()
    if not p:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{product_id}' not found"
        )

    merchant_store = current_merchant.get("store_id")
    if merchant_store and merchant_store != p.store_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unauthorized: Cannot deactivate product for store '{p.store_id}'"
        )

    p.is_active = False
    db.commit()
    return MessageResponse(
        message="Product deactivated successfully",
        detail=f"Product {product_id} marked inactive"
    )
