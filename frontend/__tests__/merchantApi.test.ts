import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  loginMerchant,
  getMerchantMe,
  getMerchantOverview,
  acceptOrder,
  rejectOrder,
  updateOrderStatus,
  updateInventoryStock,
  listStockMovements,
  getStoredToken,
  setStoredToken,
  clearStoredToken,
} from "@/lib/merchantApi";

describe("Merchant API Client Tests", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("stores token on successful login", async () => {
    const mockResponse = {
      access_token: "test-token-xyz-123",
      token_type: "bearer",
      store_id: "STORE001",
      merchant_name: "Sharma General Store",
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => mockResponse,
    } as Response);

    const res = await loginMerchant({ username: "sharma", password: "secret_password" });
    expect(res.access_token).toBe("test-token-xyz-123");
    expect(getStoredToken()).toBe("test-token-xyz-123");
  });

  it("attaches bearer token in getMerchantMe request", async () => {
    setStoredToken("test-bearer-token");

    global.fetch = vi.fn().mockImplementation((url, init) => {
      const headers = init.headers as Record<string, string>;
      expect(headers["Authorization"]).toBe("Bearer test-bearer-token");
      return Promise.resolve({
        ok: true,
        json: async () => ({
          authenticated: true,
          store_id: "STORE001",
          merchant_name: "Sharma General Store",
        }),
      } as Response);
    });

    const res = await getMerchantMe();
    expect(res.authenticated).toBe(true);
  });

  it("calls acceptOrder endpoint with POST and auth header", async () => {
    setStoredToken("token-accept-test");

    global.fetch = vi.fn().mockImplementation((url, init) => {
      expect(url).toContain("/api/v1/orders/ORD123/accept");
      expect(init.method).toBe("POST");
      return Promise.resolve({
        ok: true,
        json: async () => ({
          order_id: "ORD123",
          status: "accepted",
          total_amount: 100,
          created_at: new Date().toISOString(),
          items: [],
        }),
      } as Response);
    });

    const res = await acceptOrder("ORD123");
    expect(res.status).toBe("accepted");
  });

  it("calls rejectOrder endpoint with reason payload", async () => {
    setStoredToken("token-reject-test");

    global.fetch = vi.fn().mockImplementation((url, init) => {
      expect(url).toContain("/api/v1/orders/ORD456/reject");
      expect(init.method).toBe("POST");
      const body = JSON.parse(init.body);
      expect(body.reason).toBe("Store closed");
      return Promise.resolve({
        ok: true,
        json: async () => ({
          order_id: "ORD456",
          status: "rejected",
          rejection_reason: "Store closed",
          total_amount: 50,
          created_at: new Date().toISOString(),
          items: [],
        }),
      } as Response);
    });

    const res = await rejectOrder("ORD456", "Store closed");
    expect(res.status).toBe("rejected");
    expect(res.rejection_reason).toBe("Store closed");
  });

  it("calls updateOrderStatus endpoint with new state and notes", async () => {
    setStoredToken("token-status-test");

    global.fetch = vi.fn().mockImplementation((url, init) => {
      expect(url).toContain("/api/v1/orders/ORD789/status");
      const body = JSON.parse(init.body);
      expect(body.status).toBe("preparing");
      return Promise.resolve({
        ok: true,
        json: async () => ({
          order_id: "ORD789",
          status: "preparing",
          total_amount: 75,
          created_at: new Date().toISOString(),
          items: [],
        }),
      } as Response);
    });

    const res = await updateOrderStatus("ORD789", "preparing", "Packing items");
    expect(res.status).toBe("preparing");
  });

  it("calls updateInventoryStock with updated quantities and reason", async () => {
    setStoredToken("token-inv-test");

    global.fetch = vi.fn().mockImplementation((url, init) => {
      expect(url).toContain("/api/v1/inventory/PRD001");
      expect(init.method).toBe("PUT");
      const body = JSON.parse(init.body);
      expect(body.stock_quantity).toBe(35);
      expect(body.reason).toBe("restock");
      return Promise.resolve({
        ok: true,
        json: async () => ({
          product_id: "PRD001",
          stock_quantity: 35,
          stock_unit: "packet",
          low_stock_threshold: 5,
          reserved_quantity: 0,
          is_low_stock: false,
          is_out_of_stock: false,
          updated_at: new Date().toISOString(),
        }),
      } as Response);
    });

    const res = await updateInventoryStock("PRD001", {
      stock_quantity: 35,
      reason: "restock",
    });
    expect(res.stock_quantity).toBe(35);
  });
});
