"use client";

import React from "react";
import {
  History,
  TrendingDown,
  TrendingUp,
  Search,
  RefreshCw,
} from "lucide-react";
import { StockMovement } from "@/types/merchant";

interface StockHistoryTabProps {
  movements: StockMovement[];
  isLoading: boolean;
  onRefresh: () => void;
  productIdFilter: string;
  onFilterChange: (id: string) => void;
}

export function StockHistoryTab({
  movements,
  isLoading,
  onRefresh,
  productIdFilter,
  onFilterChange,
}: StockHistoryTabProps) {
  const reasonLabels: Record<string, { label: string; bg: string; text: string }> = {
    order_acceptance: {
      label: "Order Sweekar (Deduction)",
      bg: "bg-blue-100",
      text: "text-blue-800",
    },
    manual_adjustment: {
      label: "Manual Sudhaar",
      bg: "bg-purple-100",
      text: "text-purple-800",
    },
    order_cancelled_restock: {
      label: "Order Radd (Restock)",
      bg: "bg-emerald-100",
      text: "text-emerald-800",
    },
    supplier_delivery_restock: {
      label: "Naya Stock Aaya",
      bg: "bg-emerald-100",
      text: "text-emerald-800",
    },
    damage_expiry_writeoff: {
      label: "Kharab/Expiry Saman",
      bg: "bg-rose-100",
      text: "text-rose-800",
    },
  };

  return (
    <div className="space-y-6">
      {/* Controls Bar */}
      <div className="bg-dukaan-card border border-dukaan-border rounded-2xl p-4 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-dukaan-muted">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={productIdFilter}
            onChange={(e) => onFilterChange(e.target.value)}
            placeholder="Filter by Product ID (e.g. PRD001)..."
            className="w-full pl-9 pr-3.5 py-2 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl text-dukaan-text focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
          />
        </div>

        <button
          onClick={onRefresh}
          className="w-full sm:w-auto flex items-center justify-center gap-1.5 py-2 px-3 text-xs font-semibold rounded-xl border border-dukaan-border hover:bg-dukaan-canvas text-dukaan-text transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Audit Log Refresh</span>
        </button>
      </div>

      {/* Movements Table */}
      <div className="bg-dukaan-card border border-dukaan-border rounded-2xl shadow-warm overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-dukaan-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-dukaan-primary" />
            <h2 className="text-sm font-bold text-dukaan-text">
              Stock Movement Audit Feed ({movements.length})
            </h2>
          </div>
          <span className="text-xs text-dukaan-muted">
            Authoritative DB Records
          </span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-xs text-dukaan-muted flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-dukaan-primary" />
            <span>Audit trail prapt ho rahi hai...</span>
          </div>
        ) : movements.length === 0 ? (
          <div className="p-12 text-center text-xs text-dukaan-muted">
            Koi stock movement record nahi mila.
          </div>
        ) : (
          <div
            tabIndex={0}
            role="region"
            aria-label="Stock movement audit feed"
            className="overflow-x-auto"
          >
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-dukaan-canvas text-dukaan-muted uppercase text-[10px] font-bold tracking-wider border-b border-dukaan-border">
                <tr>
                  <th className="py-3 px-4">Movement ID</th>
                  <th className="py-3 px-4">Product / SKU</th>
                  <th className="py-3 px-4">Order ID</th>
                  <th className="py-3 px-4">Parivartan (Change)</th>
                  <th className="py-3 px-4">Karan (Reason)</th>
                  <th className="py-3 px-4 text-right">Samay (Timestamp)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dukaan-border/60">
                {movements.map((m) => {
                  const isPositive = m.change_quantity > 0;
                  const reasonInfo = reasonLabels[m.reason] || {
                    label: m.reason,
                    bg: "bg-stone-100",
                    text: "text-stone-700",
                  };
                  const dateStr = new Date(m.created_at).toLocaleString("en-IN", {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  });

                  return (
                    <tr
                      key={m.movement_id}
                      className="hover:bg-dukaan-canvas/60 transition-colors"
                    >
                      <td className="py-3.5 px-4 font-mono font-bold text-dukaan-text">
                        {m.movement_id}
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-dukaan-text">
                        <div>{m.product_name || m.product_id}</div>
                        <span className="text-[10px] font-mono text-dukaan-muted">
                          {m.product_id}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-mono text-dukaan-muted">
                        {m.order_id ? `#${m.order_id}` : "—"}
                      </td>
                      <td className="py-3.5 px-4 font-mono font-bold whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1 ${
                            isPositive ? "text-emerald-700" : "text-rose-700"
                          }`}
                        >
                          {isPositive ? (
                            <TrendingUp className="w-3.5 h-3.5" />
                          ) : (
                            <TrendingDown className="w-3.5 h-3.5" />
                          )}
                          {isPositive ? `+${m.change_quantity}` : m.change_quantity}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${reasonInfo.bg} ${reasonInfo.text}`}
                        >
                          {reasonInfo.label}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right text-dukaan-muted whitespace-nowrap font-mono text-[11px]">
                        {dateStr}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
