/**
 * DukaanSaathi — Merchant Types & Interfaces (Phase 6)
 * Strict typing synchronized with FastAPI Phase 6 endpoints.
 */

import { Order, OrderItem } from "./api";

export interface MerchantLoginRequest {
  username: string;
  password: string;
}

export interface MerchantLoginResponse {
  access_token: string;
  token_type: string;
  store_id: string;
  merchant_name: string;
}

export interface MerchantMeResponse {
  authenticated: boolean;
  store_id: string;
  merchant_name: string;
}

export interface MerchantOverviewResponse {
  store_id: string;
  store_name: string;
  pending_orders_count: number;
  today_orders_count: number;
  completed_orders_count: number;
  total_sales_inr: number;
  low_stock_products_count: number;
  out_of_stock_count: number;
  total_products_count: number;
  recent_orders: Order[];
  generated_at: string;
}

export interface InventoryItem {
  product_id: string;
  stock_quantity: number;
  stock_unit: string;
  low_stock_threshold: number;
  reserved_quantity: number;
  is_low_stock: boolean;
  is_out_of_stock: boolean;
  updated_at: string;
  // Enriched product metadata if joined
  name?: string;
  price?: number;
  category?: string;
}

export interface InventoryUpdateRequest {
  stock_quantity: number;
  low_stock_threshold?: number;
  reason?: string;
}

export interface StockMovement {
  movement_id: string;
  product_id: string;
  product_name?: string | null;
  order_id?: string | null;
  change_quantity: number;
  reason: string;
  created_at: string;
}

export interface ProductAlias {
  alias_id?: string;
  alias_text: string;
  language: string;
  confidence_score?: number;
}

export interface Product {
  product_id: string;
  store_id: string;
  name: string;
  canonical_name: string;
  brand?: string | null;
  category: string;
  sub_category?: string | null;
  barcode?: string | null;
  base_unit: string;
  package_type: string;
  package_quantity: number;
  package_unit: string;
  price: number;
  tax_rate: number;
  is_active: boolean;
  is_loose_item: boolean;
  aliases?: ProductAlias[];
  created_at?: string;
  updated_at?: string;
}

export interface ProductCreateRequest {
  store_id?: string;
  name: string;
  canonical_name?: string;
  brand?: string;
  category: string;
  sub_category?: string;
  base_unit?: string;
  package_type?: string;
  package_quantity?: number;
  package_unit?: string;
  price: number;
  is_active?: boolean;
  is_loose_item?: boolean;
  initial_stock?: number;
  low_stock_threshold?: number;
  aliases?: string[];
}

export interface ProductUpdateRequest {
  name?: string;
  canonical_name?: string;
  brand?: string;
  category?: string;
  sub_category?: string;
  base_unit?: string;
  package_type?: string;
  package_quantity?: number;
  package_unit?: string;
  price?: number;
  is_active?: boolean;
  is_loose_item?: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  has_more: boolean;
}

