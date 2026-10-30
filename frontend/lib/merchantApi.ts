/**
 * DukaanSaathi — Merchant API Client (Phase 6)
 * Securely handles merchant authentication, dashboard aggregates, order management,
 * inventory adjustments, and product catalog updates.
 */

import {
  MerchantLoginRequest,
  MerchantLoginResponse,
  MerchantMeResponse,
  MerchantOverviewResponse,
  InventoryItem,
  InventoryUpdateRequest,
  StockMovement,
  Product,
  ProductCreateRequest,
  ProductUpdateRequest,
  PaginatedResponse,
} from "@/types/merchant";
import { Order } from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

const TOKEN_KEY = "dukaansaathi_merchant_token";

export class MerchantApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "MerchantApiError";
    this.status = status;
    this.data = data;
  }
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function clearStoredToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    let errorData: unknown = null;
    try {
      errorData = await response.json();
      if (typeof errorData === "object" && errorData !== null && "detail" in errorData) {
        const detailVal = (errorData as { detail: unknown }).detail;
        errorDetail =
          typeof detailVal === "string"
            ? detailVal
            : JSON.stringify(detailVal);
      }
    } catch {
      // not JSON
    }
    throw new MerchantApiError(errorDetail, response.status, errorData);
  }
  return response.json();
}

function getAuthHeaders(): HeadersInit {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Merchant Login via backend password validation.
 */
export async function loginMerchant(
  credentials: MerchantLoginRequest
): Promise<MerchantLoginResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });
  const data = await handleResponse<MerchantLoginResponse>(res);
  if (data.access_token) {
    setStoredToken(data.access_token);
  }
  return data;
}

/**
 * Validate current merchant session.
 */
export async function getMerchantMe(): Promise<MerchantMeResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return handleResponse<MerchantMeResponse>(res);
}

/**
 * Terminate merchant session and clear client credentials.
 */
export async function logoutMerchant(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
  } catch {
    // Ignore network failure on logout
  } finally {
    clearStoredToken();
  }
}

/**
 * Merchant Dashboard Overview Metrics.
 */
export async function getMerchantOverview(): Promise<MerchantOverviewResponse> {
  const res = await fetch(`${API_BASE_URL}/api/v1/merchant/overview`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return handleResponse<MerchantOverviewResponse>(res);
}

/**
 * List orders with status filter & pagination.
 */
export async function listOrders(
  statusFilter?: string,
  page: number = 1,
  size: number = 20
): Promise<PaginatedResponse<Order>> {
  const params = new URLSearchParams({
    page: page.toString(),
    size: size.toString(),
  });
  if (statusFilter && statusFilter !== "all") {
    params.append("status", statusFilter);
  }

  const res = await fetch(`${API_BASE_URL}/api/v1/orders?${params.toString()}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return handleResponse<PaginatedResponse<Order>>(res);
}

/**
 * Get individual order details.
 */
export async function getOrder(orderId: string): Promise<Order> {
  const res = await fetch(`${API_BASE_URL}/api/v1/orders/${orderId}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return handleResponse<Order>(res);
}

/**
 * Accept a pending order atomically. Deducts stock.
 */
export async function acceptOrder(orderId: string): Promise<Order> {
  const res = await fetch(`${API_BASE_URL}/api/v1/orders/${orderId}/accept`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return handleResponse<Order>(res);
}

/**
 * Reject a pending order. Zero stock deduction.
 */
export async function rejectOrder(
  orderId: string,
  reason: string = "Dukaan par uplabdh nahi hai"
): Promise<Order> {
  const res = await fetch(`${API_BASE_URL}/api/v1/orders/${orderId}/reject`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ reason }),
  });
  return handleResponse<Order>(res);
}

/**
 * Advance order lifecycle or cancel.
 */
export async function updateOrderStatus(
  orderId: string,
  targetStatus: "preparing" | "ready" | "completed" | "cancelled",
  notes?: string
): Promise<Order> {
  const res = await fetch(`${API_BASE_URL}/api/v1/orders/${orderId}/status`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ status: targetStatus, notes }),
  });
  return handleResponse<Order>(res);
}

/**
 * List inventory items with stock filters.
 */
export async function listInventory(
  page: number = 1,
  size: number = 50,
  onlyLowStock: boolean = false,
  onlyOutOfStock: boolean = false
): Promise<PaginatedResponse<InventoryItem>> {
  const params = new URLSearchParams({
    page: page.toString(),
    size: size.toString(),
  });
  if (onlyLowStock) params.append("only_low_stock", "true");
  if (onlyOutOfStock) params.append("only_out_of_stock", "true");

  const res = await fetch(`${API_BASE_URL}/api/v1/inventory?${params.toString()}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return handleResponse<PaginatedResponse<InventoryItem>>(res);
}

/**
 * Update stock level and threshold for an item with an audit reason.
 */
export async function updateInventoryStock(
  productId: string,
  update: InventoryUpdateRequest
): Promise<InventoryItem> {
  const res = await fetch(`${API_BASE_URL}/api/v1/inventory/${productId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(update),
  });
  return handleResponse<InventoryItem>(res);
}

/**
 * List products or search products.
 */
export async function listProducts(
  page: number = 1,
  size: number = 50,
  search?: string
): Promise<PaginatedResponse<Product>> {
  let url = `${API_BASE_URL}/api/v1/products?page=${page}&size=${size}`;
  if (search && search.trim().length > 0) {
    url = `${API_BASE_URL}/api/v1/products/search?q=${encodeURIComponent(search.trim())}&page=${page}&size=${size}`;
  }

  const res = await fetch(url, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return handleResponse<PaginatedResponse<Product>>(res);
}

/**
 * Create a new product in store catalogue (Merchant Protected).
 */
export async function createProduct(
  productData: ProductCreateRequest
): Promise<Product> {
  const res = await fetch(`${API_BASE_URL}/api/v1/products`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(productData),
  });
  return handleResponse<Product>(res);
}

/**
 * Update an existing product (Merchant Protected).
 */
export async function updateProduct(
  productId: string,
  productData: ProductUpdateRequest
): Promise<Product> {
  const res = await fetch(`${API_BASE_URL}/api/v1/products/${productId}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(productData),
  });
  return handleResponse<Product>(res);
}

/**
 * List recorded stock movements and audit trail.
 */
export async function listStockMovements(
  page: number = 1,
  size: number = 20,
  productId?: string
): Promise<PaginatedResponse<StockMovement>> {
  const params = new URLSearchParams({
    page: page.toString(),
    size: size.toString(),
  });
  if (productId) params.append("product_id", productId);

  const res = await fetch(`${API_BASE_URL}/api/v1/inventory/movements?${params.toString()}`, {
    method: "GET",
    headers: getAuthHeaders(),
  });
  return handleResponse<PaginatedResponse<StockMovement>>(res);
}

