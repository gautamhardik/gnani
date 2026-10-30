/**
 * DukaanSaathi — Typed API Contracts (Phase 5)
 * Synchronized with FastAPI OpenAPI & Pydantic models.
 */

export interface Store {
  store_id: string;
  store_name: string;
  slug: string;
  currency: string;
  timezone: string;
  is_open: boolean;
  opening_time: string;
  closing_time: string;
  contact_display: string;
  description: string;
  supported_languages: string[];
}

export interface CartItem {
  product_id: string;
  name: string;
  quantity: number;
  unit: string;
  unit_price: number;
  subtotal: number;
  requested_quantity?: number | null;
  requested_unit?: string | null;
}

export interface CartSnapshot {
  items: CartItem[];
  item_count: number;
  total_amount: number;
}

export interface LatencyBreakdown {
  upload_ms: number;
  preprocessing_ms: number;
  stt_ms: number;
  intelligence_ms: number;
  tts_ms: number;
  total_ms: number;
}

export interface VoiceTurnResponse {
  session_id: string;
  turn_id: string;
  transcript: string;
  detected_language: string;
  intent: string;
  action: string;
  action_details: {
    message?: string;
    clarification_type?: string | null;
    clarification_options?: string[] | null;
    price_quote?: number | null;
    stock_quote?: number | null;
  };
  cart: CartSnapshot;
  assistant_text: string;
  session_state: string; // COLLECTING | NEEDS_CLARIFICATION | AWAITING_CONFIRMATION | ORDER_PLACED | CANCELLED
  audio_status: "generated" | "failed";
  audio_url?: string | null;
  audio_base64?: string | null;
  latency_ms: LatencyBreakdown;
  is_duplicate: boolean;
  warning?: string | null;
}

export interface OrderSession {
  session_id: string;
  store_id: string;
  customer_id?: string | null;
  status: "active" | "confirmed" | "expired";
  current_cart: CartItem[];
  created_at: string;
  updated_at: string;
}

export interface OrderSessionDetail extends OrderSession {
  total_amount: number;
  item_count: number;
}

export interface OrderItem {
  item_id: string;
  order_id: string;
  product_id: string;
  product_name_snapshot: string;
  quantity: number;
  unit: string;
  unit_price: number;
  subtotal: number;
}

export interface Order {
  order_id: string;
  store_id: string;
  session_id?: string | null;
  customer_id?: string | null;
  total_amount: number;
  status: "pending" | "accepted" | "preparing" | "ready" | "completed" | "rejected" | "cancelled";
  rejection_reason?: string | null;
  created_at: string;
  items: OrderItem[];
}

