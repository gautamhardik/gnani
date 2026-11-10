import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  getStore,
  createSession,
  getSession,
  updateCartItem,
  removeCartItem,
  sendVoiceTurn,
  getAudioPlaybackUrl,
  submitOrder,
  ApiError,
} from "@/lib/api";

describe("API Client Tests", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches store details successfully", async () => {
    const mockStore = {
      store_id: "STORE001",
      store_name: "Everyday Needs General Store",
      is_open: true,
      currency: "INR",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockStore,
    } as Response);

    const data = await getStore("STORE001");
    expect(data.store_id).toBe("STORE001");
    expect(data.store_name).toBe("Everyday Needs General Store");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/stores/STORE001"),
      expect.anything()
    );
  });

  it("creates a customer session", async () => {
    const mockSession = {
      session_id: "SESS12345",
      store_id: "STORE001",
      status: "active",
      current_cart: [],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockSession,
    } as Response);

    const session = await createSession("STORE001");
    expect(session.session_id).toBe("SESS12345");
    expect(session.status).toBe("active");
  });

  it("updates cart item via backend API", async () => {
    const mockUpdated = {
      session_id: "SESS12345",
      current_cart: [
        { product_id: "PRD001", quantity: 3, unit_price: 14.0, subtotal: 42.0 },
      ],
      total_amount: 42.0,
      item_count: 1,
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockUpdated,
    } as Response);

    const res = await updateCartItem("SESS12345", "PRD001", 3);
    expect(res.item_count).toBe(1);
    expect(res.total_amount).toBe(42.0);
  });

  it("removes cart item via backend API", async () => {
    const mockEmpty = {
      session_id: "SESS12345",
      current_cart: [],
      total_amount: 0.0,
      item_count: 0,
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockEmpty,
    } as Response);

    const res = await removeCartItem("SESS12345", "PRD001");
    expect(res.item_count).toBe(0);
    expect(res.total_amount).toBe(0.0);
  });

  it("handles server error responses with ApiError", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ detail: "Insufficient stock available" }),
    } as Response);

    await expect(updateCartItem("SESS12345", "PRD001", 999)).rejects.toThrow(
      ApiError
    );
  });

  it("constructs correct audio playback URL", () => {
    const url1 = getAudioPlaybackUrl("/api/v1/voice/audio/aud_123");
    expect(url1).toContain("/api/v1/voice/audio/aud_123");

    const url2 = getAudioPlaybackUrl("aud_456");
    expect(url2).toContain("/api/v1/voice/audio/aud_456");
  });

  it("submits customer order with pending status", async () => {
    const mockOrder = {
      order_id: "ORD9876",
      status: "pending",
      total_amount: 145.0,
      items: [{ item_id: "ITM1", product_id: "PRD001", quantity: 2, subtotal: 28.0 }],
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockOrder,
    } as Response);

    const order = await submitOrder("SESS12345", "STORE001", [
      { product_id: "PRD001", quantity: 2 },
    ]);
    expect(order.order_id).toBe("ORD9876");
    expect(order.status).toBe("pending");
  });
});

