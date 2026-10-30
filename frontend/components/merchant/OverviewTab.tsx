"use client";

import React from "react";
import {
  Clock,
  ShoppingBag,
  CheckCircle2,
  IndianRupee,
  AlertTriangle,
  ArrowRight,
} from "lucide-react";
import { MerchantOverviewResponse } from "@/types/merchant";
import { Order } from "@/types/api";

interface OverviewTabProps {
  overview: MerchantOverviewResponse | null;
  onNavigateTab: (tab: "orders" | "inventory" | "products" | "movements") => void;
  onSelectOrder: (order: Order) => void;
}

export function OverviewTab({
  overview,
  onNavigateTab,
  onSelectOrder,
}: OverviewTabProps) {
  if (!overview) {
    return (
      <div className="p-8 text-center text-sm text-dukaan-muted">
        Aakde prapt kiye ja rahe hain... (Loading overview...)
      </div>
    );
  }

  const statusColors: Record<string, { bg: string; text: string; label: string }> = {
    pending: { bg: "bg-amber-100", text: "text-amber-800", label: "Pending (लंबित)" },
    accepted: { bg: "bg-blue-100", text: "text-blue-800", label: "Accepted (स्वीकृत)" },
    preparing: { bg: "bg-purple-100", text: "text-purple-800", label: "Preparing (तैयार हो रहा)" },
    ready: { bg: "bg-teal-100", text: "text-teal-800", label: "Ready (तैयार)" },
    completed: { bg: "bg-emerald-100", text: "text-emerald-800", label: "Completed (पूरा हुआ)" },
    rejected: { bg: "bg-rose-100", text: "text-rose-800", label: "Rejected (अस्वीकृत)" },
    cancelled: { bg: "bg-stone-200", text: "text-stone-700", label: "Cancelled (रद्द)" },
  };

  return (
    <div className="space-y-6">
      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4">
        {/* Pending Orders */}
        <div
          onClick={() => onNavigateTab("orders")}
          className={`cursor-pointer rounded-2xl p-4 sm:p-5 border transition-all ${
            overview.pending_orders_count > 0
              ? "bg-amber-50/70 border-amber-300 shadow-warm hover:shadow-floating"
              : "bg-dukaan-card border-dukaan-border hover:border-dukaan-accent/40"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-dukaan-muted">
              Pending Orders (लंबित)
            </span>
            <div
              className={`w-8 h-8 rounded-xl flex items-center justify-center ${
                overview.pending_orders_count > 0
                  ? "bg-amber-500 text-white animate-pulse"
                  : "bg-dukaan-canvas text-dukaan-muted"
              }`}
            >
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-extrabold text-dukaan-text">
              {overview.pending_orders_count}
            </span>
            <p className="text-[11px] text-dukaan-muted mt-0.5">
              {overview.pending_orders_count > 0
                ? "Turant dhyan dein (Accept/Reject)"
                : "Sabhi orders process ho gaye"}
            </p>
          </div>
        </div>

        {/* Today's Orders */}
        <div className="bg-dukaan-card rounded-2xl p-4 sm:p-5 border border-dukaan-border shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-dukaan-muted">
              Aaj Ke Orders (Today)
            </span>
            <div className="w-8 h-8 rounded-xl bg-dukaan-canvas flex items-center justify-center text-dukaan-primary">
              <ShoppingBag className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-extrabold text-dukaan-text">
              {overview.today_orders_count}
            </span>
            <p className="text-[11px] text-dukaan-muted mt-0.5">
              Aaj prapt kul orders
            </p>
          </div>
        </div>

        {/* Completed Orders */}
        <div className="bg-dukaan-card rounded-2xl p-4 sm:p-5 border border-dukaan-border shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-dukaan-muted">
              Completed (पूरे हुए)
            </span>
            <div className="w-8 h-8 rounded-xl bg-dukaan-successBg flex items-center justify-center text-dukaan-success">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-extrabold text-dukaan-text">
              {overview.completed_orders_count}
            </span>
            <p className="text-[11px] text-dukaan-muted mt-0.5">
              Safaltapoorvak vitrit
            </p>
          </div>
        </div>

        {/* Total Realized Sales */}
        <div className="bg-dukaan-card rounded-2xl p-4 sm:p-5 border border-dukaan-border shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-dukaan-muted">
              Kul Bikri (Total Sales)
            </span>
            <div className="w-8 h-8 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
              <IndianRupee className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-1">
              <span className="text-xs font-bold text-dukaan-text">₹</span>
              <span className="text-2xl sm:text-3xl font-extrabold text-dukaan-text">
                {Number(overview.total_sales_inr).toLocaleString("en-IN", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </span>
            </div>
            <p className="text-[11px] text-dukaan-muted mt-0.5">
              Accepted/Completed Bikri
            </p>
          </div>
        </div>

        {/* Low Stock Alerts */}
        <div
          onClick={() => onNavigateTab("inventory")}
          className={`cursor-pointer rounded-2xl p-4 sm:p-5 border transition-all col-span-2 lg:col-span-1 ${
            overview.low_stock_products_count > 0
              ? "bg-rose-50/60 border-rose-200 hover:shadow-warm"
              : "bg-dukaan-card border-dukaan-border"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-dukaan-muted">
              Kam Stock Alert (Low Stock)
            </span>
            <div
              className={`w-8 h-8 rounded-xl flex items-center justify-center ${
                overview.low_stock_products_count > 0
                  ? "bg-rose-500 text-white"
                  : "bg-dukaan-canvas text-dukaan-muted"
              }`}
            >
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-extrabold text-dukaan-text">
              {overview.low_stock_products_count}
            </span>
            <p className="text-[11px] text-rose-700 mt-0.5">
              {overview.out_of_stock_count > 0
                ? `${overview.out_of_stock_count} out-of-stock items`
                : "Products reorder karein"}
            </p>
          </div>
        </div>
      </div>

      {/* Recent Orders Section */}
      <div className="bg-dukaan-card border border-dukaan-border rounded-2xl p-5 sm:p-6 shadow-warm">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-base font-bold text-dukaan-text">
              Haal Hi Ke Orders (Recent Orders)
            </h2>
            <p className="text-xs text-dukaan-muted">
              Antim 5 orders ki live sthiti
            </p>
          </div>
          <button
            onClick={() => onNavigateTab("orders")}
            className="flex items-center gap-1 text-xs font-bold text-dukaan-primary hover:text-dukaan-primaryDark transition-colors"
          >
            <span>Sabhi Dekhein (View All)</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {overview.recent_orders.length === 0 ? (
          <div className="text-center py-8 text-xs text-dukaan-muted border border-dashed border-dukaan-border rounded-xl">
            Abhi tak koi order prapt nahi hua hai.
          </div>
        ) : (
          <div className="divide-y divide-dukaan-border/60">
            {overview.recent_orders.map((order) => {
              const badge = statusColors[order.status] || {
                bg: "bg-stone-100",
                text: "text-stone-700",
                label: order.status,
              };
              const dateStr = new Date(order.created_at).toLocaleTimeString("en-IN", {
                hour: "2-digit",
                minute: "2-digit",
              });

              return (
                <div
                  key={order.order_id}
                  onClick={() => onSelectOrder(order)}
                  className="py-3.5 flex items-center justify-between hover:bg-dukaan-canvas/60 rounded-xl px-2 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-dukaan-canvas border border-dukaan-border flex items-center justify-center text-xs font-mono font-bold text-dukaan-text">
                      #{order.order_id.slice(-4)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-dukaan-text">
                          Order #{order.order_id}
                        </span>
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${badge.bg} ${badge.text}`}
                        >
                          {badge.label}
                        </span>
                      </div>
                      <p className="text-[11px] text-dukaan-muted mt-0.5">
                        {order.items?.length || 0} saman • {dateStr}
                      </p>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-xs font-bold text-dukaan-text font-mono">
                      ₹{Number(order.total_amount).toFixed(2)}
                    </span>
                    <p className="text-[10px] text-dukaan-primary font-semibold mt-0.5 flex items-center justify-end gap-0.5">
                      Vistrit Dekhein <ArrowRight className="w-2.5 h-2.5" />
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
