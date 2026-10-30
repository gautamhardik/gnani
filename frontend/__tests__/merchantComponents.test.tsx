import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MerchantHeader } from "@/components/merchant/MerchantHeader";
import { OverviewTab } from "@/components/merchant/OverviewTab";
import { OrdersTab } from "@/components/merchant/OrdersTab";
import { MerchantOverviewResponse, InventoryItem } from "@/types/merchant";
import { Order } from "@/types/api";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

const mockOverview: MerchantOverviewResponse = {
  store_id: "STORE001",
  store_name: "Sharma General Store (Demo)",
  pending_orders_count: 3,
  today_orders_count: 12,
  completed_orders_count: 8,
  total_sales_inr: 2450.5,
  low_stock_products_count: 4,
  out_of_stock_count: 1,
  total_products_count: 100,
  recent_orders: [
    {
      order_id: "ORD0001",
      store_id: "STORE001",
      total_amount: 140,
      status: "pending",
      created_at: new Date().toISOString(),
      items: [
        {
          item_id: "ITEM001",
          order_id: "ORD0001",
          product_id: "PRD001",
          product_name_snapshot: "Amul Taaza Milk 500ml",
          quantity: 2,
          unit: "packet",
          unit_price: 27,
          subtotal: 54,
        },
      ],
    },
  ],
  generated_at: new Date().toISOString(),
};

const mockOrders: Order[] = [
  {
    order_id: "ORD0001",
    store_id: "STORE001",
    total_amount: 140,
    status: "pending",
    created_at: new Date().toISOString(),
    items: [
      {
        item_id: "ITEM001",
        order_id: "ORD0001",
        product_id: "PRD001",
        product_name_snapshot: "Amul Taaza Milk 500ml",
        quantity: 2,
        unit: "packet",
        unit_price: 27,
        subtotal: 54,
      },
    ],
  },
  {
    order_id: "ORD0002",
    store_id: "STORE001",
    total_amount: 320,
    status: "accepted",
    created_at: new Date().toISOString(),
    items: [],
  },
];

describe("Merchant Dashboard UI Component Tests", () => {
  it("renders MerchantHeader with store title and live store indicator", () => {
    render(
      <MerchantHeader
        storeName="Sharma General Store (Demo)"
        onRefresh={vi.fn()}
        isRefreshing={false}
      />
    );

    expect(screen.getByText("Sharma General Store (Demo)")).toBeInTheDocument();
    expect(screen.getByText("Live Store")).toBeInTheDocument();
    expect(screen.getByText(/Dukandar Operations Portal/i)).toBeInTheDocument();
  });

  it("renders OverviewTab metrics and recent orders accurately", () => {
    const onNavigateTab = vi.fn();
    const onSelectOrder = vi.fn();

    render(
      <OverviewTab
        overview={mockOverview}
        onNavigateTab={onNavigateTab}
        onSelectOrder={onSelectOrder}
      />
    );

    // Assert metric counters
    expect(screen.getByText("3")).toBeInTheDocument(); // pending count
    expect(screen.getByText("12")).toBeInTheDocument(); // today count
    expect(screen.getByText("8")).toBeInTheDocument(); // completed count
    expect(screen.getByText("2,450.50")).toBeInTheDocument(); // sales INR
    expect(screen.getByText("4")).toBeInTheDocument(); // low stock count

    // Assert recent order rendered
    expect(screen.getByText("Order #ORD0001")).toBeInTheDocument();
  });

  it("renders OrdersTab status filters and order table", () => {
    const onSelectStatus = vi.fn();
    const onRefresh = vi.fn();
    const onSelectOrder = vi.fn();

    render(
      <OrdersTab
        orders={mockOrders}
        selectedStatus="all"
        onSelectStatus={onSelectStatus}
        onRefresh={onRefresh}
        selectedOrder={mockOrders[0]}
        onSelectOrder={onSelectOrder}
      />
    );

    // Assert status filter pills
    expect(screen.getByText("Sabhi (All)")).toBeInTheDocument();
    expect(screen.getByText("Pending (लंबित)")).toBeInTheDocument();

    // Assert orders listed
    expect(screen.getByText("#ORD0001")).toBeInTheDocument();
    expect(screen.getByText("#ORD0002")).toBeInTheDocument();

    // Assert selected order details visible
    expect(screen.getByText("Amul Taaza Milk 500ml")).toBeInTheDocument();
    expect(screen.getByText(/Accept \(स्वीकार\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Reject \(अस्वीकार\)/i)).toBeInTheDocument();
  });
});
