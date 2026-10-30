"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  ShoppingBag,
  Boxes,
  PackagePlus,
  History,
  AlertCircle,
  Loader2,
} from "lucide-react";
import {
  getMerchantMe,
  getMerchantOverview,
  listOrders,
  listInventory,
  listProducts,
  listStockMovements,
  getStoredToken,
} from "@/lib/merchantApi";
import {
  MerchantOverviewResponse,
  InventoryItem,
  Product,
  StockMovement,
} from "@/types/merchant";
import { Order } from "@/types/api";

import { MerchantHeader } from "@/components/merchant/MerchantHeader";
import { OverviewTab } from "@/components/merchant/OverviewTab";
import { OrdersTab } from "@/components/merchant/OrdersTab";
import { InventoryTab } from "@/components/merchant/InventoryTab";
import { ProductsTab } from "@/components/merchant/ProductsTab";
import { StockHistoryTab } from "@/components/merchant/StockHistoryTab";

type TabId = "overview" | "orders" | "inventory" | "products" | "movements";

export default function MerchantDashboardPage() {
  const router = useRouter();

  // Auth & Page loading state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authChecking, setAuthChecking] = useState(true);
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  // Tab Data States
  const [overview, setOverview] = useState<MerchantOverviewResponse | null>(null);

  // Orders State
  const [orders, setOrders] = useState<Order[]>([]);
  const [selectedOrderStatus, setSelectedOrderStatus] = useState<string>("all");
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);

  // Inventory State
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [inventoryLoading, setInventoryLoading] = useState(false);
  const [onlyLowStock, setOnlyLowStock] = useState(false);
  const [onlyOutOfStock, setOnlyOutOfStock] = useState(false);

  // Products State
  const [products, setProducts] = useState<Product[]>([]);
  const [productsLoading, setProductsLoading] = useState(false);
  const [productSearch, setProductSearch] = useState("");

  // Stock Movements State
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [movementsLoading, setMovementsLoading] = useState(false);
  const [movementProductFilter, setMovementProductFilter] = useState("");

  // Step 1: Verify Auth
  useEffect(() => {
    async function checkAuth() {
      const token = getStoredToken();
      if (!token) {
        router.push("/merchant/login");
        return;
      }

      try {
        await getMerchantMe();
        setIsAuthenticated(true);
      } catch {
        router.push("/merchant/login");
      } finally {
        setAuthChecking(false);
      }
    }
    checkAuth();
  }, [router]);

  // Step 2: Fetch Overview
  const fetchOverview = useCallback(async () => {
    try {
      const data = await getMerchantOverview();
      setOverview(data);
    } catch (err: unknown) {
      setGlobalError(err instanceof Error ? err.message : "Failed to load overview");
    }
  }, []);

  // Step 3: Fetch Orders
  const fetchOrders = useCallback(async () => {
    try {
      const res = await listOrders(selectedOrderStatus, 1, 50);
      setOrders(res.items);
      // Keep selected order in sync if it exists
      if (selectedOrder) {
        const found = res.items.find((o) => o.order_id === selectedOrder.order_id);
        if (found) setSelectedOrder(found);
      }
    } catch (err: unknown) {
      console.error("Order fetch error:", err);
    }
  }, [selectedOrderStatus, selectedOrder]);

  // Step 4: Fetch Inventory
  const fetchInventory = useCallback(async () => {
    setInventoryLoading(true);
    try {
      const res = await listInventory(1, 100, onlyLowStock, onlyOutOfStock);
      setInventory(res.items);
    } catch (err: unknown) {
      console.error("Inventory fetch error:", err);
    } finally {
      setInventoryLoading(false);
    }
  }, [onlyLowStock, onlyOutOfStock]);

  // Step 5: Fetch Products
  const fetchProducts = useCallback(async () => {
    setProductsLoading(true);
    try {
      const res = await listProducts(1, 100, productSearch);
      setProducts(res.items);
    } catch (err: unknown) {
      console.error("Products fetch error:", err);
    } finally {
      setProductsLoading(false);
    }
  }, [productSearch]);

  // Step 6: Fetch Stock Movements
  const fetchMovements = useCallback(async () => {
    setMovementsLoading(true);
    try {
      const res = await listStockMovements(1, 50, movementProductFilter || undefined);
      setMovements(res.items);
    } catch (err: unknown) {
      console.error("Movements fetch error:", err);
    } finally {
      setMovementsLoading(false);
    }
  }, [movementProductFilter]);

  // Comprehensive Refresh
  const handleGlobalRefresh = useCallback(async () => {
    setIsRefreshing(true);
    setGlobalError(null);
    try {
      await Promise.all([
        fetchOverview(),
        fetchOrders(),
        fetchInventory(),
        fetchProducts(),
        fetchMovements(),
      ]);
    } finally {
      setIsRefreshing(false);
    }
  }, [fetchOverview, fetchOrders, fetchInventory, fetchProducts, fetchMovements]);

  // Initial load once authenticated
  useEffect(() => {
    if (isAuthenticated) {
      handleGlobalRefresh();
    }
  }, [isAuthenticated, handleGlobalRefresh]);

  // Tab change effects
  useEffect(() => {
    if (!isAuthenticated) return;
    if (activeTab === "orders") fetchOrders();
    if (activeTab === "inventory") fetchInventory();
    if (activeTab === "products") fetchProducts();
    if (activeTab === "movements") fetchMovements();
  }, [activeTab, isAuthenticated, fetchOrders, fetchInventory, fetchProducts, fetchMovements]);

  if (authChecking) {
    return (
      <div className="min-h-screen bg-dukaan-canvas flex items-center justify-center p-4">
        <div className="flex items-center gap-2 text-xs font-semibold text-dukaan-muted">
          <Loader2 className="w-4 h-4 animate-spin text-dukaan-primary" />
          <span>Dukandar session satyaapit ho raha hai...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  const tabs: { id: TabId; label: string; icon: React.ReactNode; badge?: number }[] = [
    {
      id: "overview",
      label: "Overview (डैशबोर्ड)",
      icon: <LayoutDashboard className="w-4 h-4" />,
    },
    {
      id: "orders",
      label: "Orders (ऑर्डर कतार)",
      icon: <ShoppingBag className="w-4 h-4" />,
      badge: overview?.pending_orders_count || 0,
    },
    {
      id: "inventory",
      label: "Inventory (स्टॉक)",
      icon: <Boxes className="w-4 h-4" />,
      badge: overview?.low_stock_products_count || 0,
    },
    {
      id: "products",
      label: "Products (कैटलॉग)",
      icon: <PackagePlus className="w-4 h-4" />,
    },
    {
      id: "movements",
      label: "Stock History (ऑडिट)",
      icon: <History className="w-4 h-4" />,
    },
  ];

  return (
    <div className="min-h-screen bg-dukaan-canvas flex flex-col">
      {/* Top Header */}
      <MerchantHeader
        storeName={overview?.store_name || "Sharma General Store"}
        onRefresh={handleGlobalRefresh}
        isRefreshing={isRefreshing}
      />

      {/* Main Container */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full flex-1 flex flex-col">
        {/* Navigation Tabs Bar */}
        <nav
          aria-label="Merchant Dashboard Sections"
          className="flex items-center gap-1.5 border-b border-dukaan-border pb-3 mb-6 overflow-x-auto"
        >
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 py-2 px-3.5 rounded-xl text-xs font-bold transition-all whitespace-nowrap ${
                  isActive
                    ? "bg-dukaan-text text-white shadow-warm"
                    : "text-dukaan-muted hover:text-dukaan-text hover:bg-dukaan-card"
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span
                    className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-extrabold ${
                      tab.id === "orders"
                        ? "bg-amber-500 text-white animate-pulse"
                        : "bg-rose-500 text-white"
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Global Error Banner */}
        {globalError && (
          <div
            role="alert"
            className="mb-6 p-4 rounded-2xl bg-dukaan-errorBg border border-dukaan-error/30 flex items-center justify-between text-xs text-dukaan-error"
          >
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{globalError}</span>
            </div>
            <button
              onClick={() => setGlobalError(null)}
              className="text-dukaan-error font-bold"
            >
              ✕
            </button>
          </div>
        )}

        {/* Tab Content Panes */}
        <div className="flex-1">
          {activeTab === "overview" && (
            <OverviewTab
              overview={overview}
              onNavigateTab={(tab) => setActiveTab(tab)}
              onSelectOrder={(order) => {
                setSelectedOrder(order);
                setActiveTab("orders");
              }}
            />
          )}

          {activeTab === "orders" && (
            <OrdersTab
              orders={orders}
              selectedStatus={selectedOrderStatus}
              onSelectStatus={setSelectedOrderStatus}
              onRefresh={handleGlobalRefresh}
              selectedOrder={selectedOrder}
              onSelectOrder={setSelectedOrder}
            />
          )}

          {activeTab === "inventory" && (
            <InventoryTab
              inventory={inventory}
              isLoading={inventoryLoading}
              onRefresh={handleGlobalRefresh}
              onlyLowStock={onlyLowStock}
              setOnlyLowStock={setOnlyLowStock}
              onlyOutOfStock={onlyOutOfStock}
              setOnlyOutOfStock={setOnlyOutOfStock}
            />
          )}

          {activeTab === "products" && (
            <ProductsTab
              products={products}
              isLoading={productsLoading}
              onRefresh={handleGlobalRefresh}
              searchQuery={productSearch}
              onSearchChange={setProductSearch}
            />
          )}

          {activeTab === "movements" && (
            <StockHistoryTab
              movements={movements}
              isLoading={movementsLoading}
              onRefresh={handleGlobalRefresh}
              productIdFilter={movementProductFilter}
              onFilterChange={setMovementProductFilter}
            />
          )}
        </div>
      </div>
    </div>
  );
}

