/**
 * DukaanSaathi — Typed API Client
 * Connects Next.js to FastAPI backend without exposing any credentials.
 */

import {
  Store,
  OrderSession,
  OrderSessionDetail,
  VoiceTurnResponse,
  Order,
} from "@/types/api";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
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
    throw new ApiError(errorDetail, response.status, errorData);
  }
  return response.json();
}

/**
 * Fetch store information including open/closed status and languages.
 */
export async function getStore(storeId: string = "STORE001"): Promise<Store> {
  const res = await fetch(`${API_BASE_URL}/api/v1/stores/${storeId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  return handleResponse<Store>(res);
}

/**
 * Create or initialize a customer order session.
 */
export async function createSession(
  storeId: string = "STORE001",
  customerId?: string
): Promise<OrderSession> {
  const res = await fetch(`${API_BASE_URL}/api/v1/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      store_id: storeId,
      customer_id: customerId || null,
    }),
  });
  return handleResponse<OrderSession>(res);
}

/**
 * Retrieve session state and current cart.
 */
export async function getSession(sessionId: string): Promise<OrderSessionDetail> {
  const res = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });
  return handleResponse<OrderSessionDetail>(res);
}

/**
 * Manually update cart item quantity via authoritative backend.
 */
export async function updateCartItem(
  sessionId: string,
  productId: string,
  quantity: number
): Promise<OrderSessionDetail> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}/cart/items/${productId}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity }),
    }
  );
  return handleResponse<OrderSessionDetail>(res);
}

/**
 * Manually remove an item from the session cart.
 */
export async function removeCartItem(
  sessionId: string,
  productId: string
): Promise<OrderSessionDetail> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}/cart/items/${productId}`,
    {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
    }
  );
  return handleResponse<OrderSessionDetail>(res);
}

/**
 * Upload customer voice recording to voice turn endpoint.
 */
export async function sendVoiceTurn(
  sessionId: string,
  audioBlob: Blob,
  filename: string = "turn.webm",
  clientTurnId?: string
): Promise<VoiceTurnResponse> {
  const formData = new FormData();
  formData.append("audio_file", audioBlob, filename);
  if (clientTurnId) {
    formData.append("client_turn_id", clientTurnId);
  }

  const res = await fetch(
    `${API_BASE_URL}/api/v1/voice/sessions/${sessionId}/turn`,
    {
      method: "POST",
      body: formData,
    }
  );
  return handleResponse<VoiceTurnResponse>(res);
}

/**
 * Resolves full audio playback URL for synthesized response audio.
 */
export function getAudioPlaybackUrl(audioUrlOrId: string): string {
  if (audioUrlOrId.startsWith("http://") || audioUrlOrId.startsWith("https://")) {
    return audioUrlOrId;
  }
  if (audioUrlOrId.startsWith("/api/v1/voice/audio/")) {
    return `${API_BASE_URL}${audioUrlOrId}`;
  }
  return `${API_BASE_URL}/api/v1/voice/audio/${audioUrlOrId}`;
}

/**
 * Submits final customer order confirmation.
 * CRITICAL BUSINESS RULE:
 * Sets order status='pending'. Inventory is NOT deducted here;
 * only shopkeeper acceptance triggers stock decrement.
 */
export async function submitOrder(
  sessionId: string,
  storeId: string,
  items: Array<{ product_id: string; quantity: number }>
): Promise<Order> {
  const res = await fetch(`${API_BASE_URL}/api/v1/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      store_id: storeId,
      session_id: sessionId,
      items: items.map((it) => ({
        product_id: it.product_id,
        quantity: it.quantity,
      })),
    }),
  });
  return handleResponse<Order>(res);
}

/**
 * Retrieve order details for a customer session.
 * Requires matching session_id for authorization.
 */
export async function getCustomerOrder(
  orderId: string,
  sessionId: string
): Promise<Order> {
  const res = await fetch(
    `${API_BASE_URL}/api/v1/orders/${orderId}?session_id=${encodeURIComponent(sessionId)}`,
    {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    }
  );
  return handleResponse<Order>(res);
}
