"use client";

import React, { useState } from "react";
import {
  Search,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Edit3,
  Loader2,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { InventoryItem } from "@/types/merchant";
import { updateInventoryStock } from "@/lib/merchantApi";

interface InventoryTabProps {
  inventory: InventoryItem[];
  isLoading: boolean;
  onRefresh: () => void;
  onlyLowStock: boolean;
  setOnlyLowStock: (val: boolean) => void;
  onlyOutOfStock: boolean;
  setOnlyOutOfStock: (val: boolean) => void;
}

export function InventoryTab({
  inventory,
  isLoading,
  onRefresh,
  onlyLowStock,
  setOnlyLowStock,
  onlyOutOfStock,
  setOnlyOutOfStock,
}: InventoryTabProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null);
  const [newStock, setNewStock] = useState<string>("");
  const [newThreshold, setNewThreshold] = useState<string>("");
  const [adjustmentReason, setAdjustmentReason] = useState<string>("manual_adjustment");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  // Filter items locally by search query
  const filteredItems = inventory.filter((item) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      item.product_id.toLowerCase().includes(q) ||
      (item.name && item.name.toLowerCase().includes(q))
    );
  });

  const handleOpenEdit = (item: InventoryItem) => {
    setSelectedItem(item);
    setNewStock(item.stock_quantity.toString());
    setNewThreshold(item.low_stock_threshold.toString());
    setAdjustmentReason("manual_adjustment");
    setModalError(null);
  };

  const handleSaveStock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;

    const parsedStock = parseFloat(newStock);
    const parsedThreshold = parseFloat(newThreshold);

    if (isNaN(parsedStock) || parsedStock < 0) {
      setModalError("Kripya sahi stock sankhya daalein (>= 0).");
      return;
    }

    setIsSubmitting(true);
    setModalError(null);

    try {
      await updateInventoryStock(selectedItem.product_id, {
        stock_quantity: parsedStock,
        low_stock_threshold: isNaN(parsedThreshold) ? undefined : parsedThreshold,
        reason: adjustmentReason || "manual_adjustment",
      });
      setSelectedItem(null);
      onRefresh();
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Stock update failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Controls Bar: Search & Quick Filters */}
      <div className="bg-dukaan-card border border-dukaan-border rounded-2xl p-4 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Search */}
        <div className="relative w-full sm:w-80">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-dukaan-muted">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search SKU ya saman ka naam..."
            className="w-full pl-9 pr-3.5 py-2 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl text-dukaan-text focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
          />
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto">
          <button
            onClick={() => {
              setOnlyLowStock(false);
              setOnlyOutOfStock(false);
            }}
            className={`text-xs font-semibold px-3 py-1.5 rounded-xl border transition-colors whitespace-nowrap ${
              !onlyLowStock && !onlyOutOfStock
                ? "bg-dukaan-primary text-white border-dukaan-primary"
                : "border-dukaan-border text-dukaan-muted hover:text-dukaan-text"
            }`}
          >
            Sabhi Items
          </button>
          <button
            onClick={() => {
              setOnlyLowStock(!onlyLowStock);
              if (!onlyLowStock) setOnlyOutOfStock(false);
            }}
            className={`text-xs font-semibold px-3 py-1.5 rounded-xl border transition-colors whitespace-nowrap flex items-center gap-1 ${
              onlyLowStock
                ? "bg-amber-600 text-white border-amber-600"
                : "border-dukaan-border text-amber-700 hover:bg-amber-50"
            }`}
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Low Stock Alert</span>
          </button>
          <button
            onClick={() => {
              setOnlyOutOfStock(!onlyOutOfStock);
              if (!onlyOutOfStock) setOnlyLowStock(false);
            }}
            className={`text-xs font-semibold px-3 py-1.5 rounded-xl border transition-colors whitespace-nowrap flex items-center gap-1 ${
              onlyOutOfStock
                ? "bg-rose-600 text-white border-rose-600"
                : "border-dukaan-border text-rose-700 hover:bg-rose-50"
            }`}
          >
            <XCircle className="w-3.5 h-3.5" />
            <span>Out of Stock</span>
          </button>
        </div>
      </div>

      {/* Inventory Table */}
      <div className="bg-dukaan-card border border-dukaan-border rounded-2xl shadow-warm overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-dukaan-border flex items-center justify-between">
          <h2 className="text-sm font-bold text-dukaan-text">
            Inventory Stock Suchi ({filteredItems.length})
          </h2>
          <span className="text-xs text-dukaan-muted">
            Audited & Timestamped
          </span>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-xs text-dukaan-muted flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-dukaan-primary" />
            <span>Stock data load ho raha hai...</span>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center text-xs text-dukaan-muted">
            Koi product stock match nahi hua.
          </div>
        ) : (
          <div
            tabIndex={0}
            role="region"
            aria-label="Store inventory table"
            className="overflow-x-auto"
          >
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-dukaan-canvas text-dukaan-muted uppercase text-[10px] font-bold tracking-wider border-b border-dukaan-border">
                <tr>
                  <th className="py-3 px-4">SKU / ID</th>
                  <th className="py-3 px-4">Product Name</th>
                  <th className="py-3 px-4">Stock Quantity</th>
                  <th className="py-3 px-4">Low Stock Limit</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Badlein (Update)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dukaan-border/60">
                {filteredItems.map((item) => {
                  let statusBadge = (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800">
                      <CheckCircle2 className="w-3 h-3" />
                      In Stock
                    </span>
                  );

                  if (item.is_out_of_stock || item.stock_quantity === 0) {
                    statusBadge = (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-rose-100 text-rose-800">
                        <XCircle className="w-3 h-3" />
                        Out of Stock
                      </span>
                    );
                  } else if (item.is_low_stock || item.stock_quantity <= item.low_stock_threshold) {
                    statusBadge = (
                      <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">
                        <AlertTriangle className="w-3 h-3" />
                        Low Stock
                      </span>
                    );
                  }

                  return (
                    <tr
                      key={item.product_id}
                      className="hover:bg-dukaan-canvas/60 transition-colors"
                    >
                      <td className="py-3 px-4 font-mono font-bold text-dukaan-text">
                        {item.product_id}
                      </td>
                      <td className="py-3 px-4 font-medium text-dukaan-text">
                        {item.name || item.product_id}
                      </td>
                      <td className="py-3 px-4 font-mono font-bold text-dukaan-text">
                        {item.stock_quantity} {item.stock_unit}
                      </td>
                      <td className="py-3 px-4 text-dukaan-muted font-mono">
                        {item.low_stock_threshold} {item.stock_unit}
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        {statusBadge}
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap">
                        <button
                          onClick={() => handleOpenEdit(item)}
                          className="inline-flex items-center gap-1 py-1 px-2.5 bg-dukaan-canvas hover:bg-dukaan-border border border-dukaan-border text-dukaan-text text-[11px] font-semibold rounded-lg transition-colors"
                        >
                          <Edit3 className="w-3 h-3 text-dukaan-muted" />
                          <span>Update</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Edit Stock Modal */}
      {selectedItem && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4"
        >
          <div className="bg-dukaan-card border border-dukaan-border rounded-2xl p-6 max-w-md w-full shadow-floating animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-dukaan-text">
                  Stock Badlein (Adjust Stock)
                </h3>
                <p className="text-xs text-dukaan-muted font-mono mt-0.5">
                  {selectedItem.product_id} • {selectedItem.name || "Product"}
                </p>
              </div>
              <button
                onClick={() => setSelectedItem(null)}
                className="text-dukaan-muted hover:text-dukaan-text text-sm"
              >
                ✕
              </button>
            </div>

            {modalError && (
              <div
                role="alert"
                className="mb-4 p-3 rounded-xl bg-dukaan-errorBg border border-dukaan-error/30 flex items-start gap-2 text-xs text-dukaan-error"
              >
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{modalError}</span>
              </div>
            )}

            <form onSubmit={handleSaveStock} className="space-y-4">
              <div>
                <label
                  htmlFor="new-stock"
                  className="block text-xs font-semibold text-dukaan-text mb-1"
                >
                  Naya Stock ({selectedItem.stock_unit}):
                </label>
                <input
                  id="new-stock"
                  type="number"
                  step="any"
                  min="0"
                  required
                  value={newStock}
                  onChange={(e) => setNewStock(e.target.value)}
                  className="w-full py-2 px-3 text-sm bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                />
              </div>

              <div>
                <label
                  htmlFor="new-threshold"
                  className="block text-xs font-semibold text-dukaan-text mb-1"
                >
                  Low Stock Alert Seema (Threshold):
                </label>
                <input
                  id="new-threshold"
                  type="number"
                  step="any"
                  min="0"
                  value={newThreshold}
                  onChange={(e) => setNewThreshold(e.target.value)}
                  className="w-full py-2 px-3 text-sm bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                />
              </div>

              <div>
                <label
                  htmlFor="adjustment-reason"
                  className="block text-xs font-semibold text-dukaan-text mb-1"
                >
                  Audit Karan (Reason for Change):
                </label>
                <select
                  id="adjustment-reason"
                  value={adjustmentReason}
                  onChange={(e) => setAdjustmentReason(e.target.value)}
                  className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
                >
                  <option value="manual_adjustment">Manual Adjustment (मैनुअल सुधार)</option>
                  <option value="supplier_delivery_restock">Naya Stock Aaya (Supplier Delivery)</option>
                  <option value="damage_expiry_writeoff">Kharab / Expiry Saman (Writeoff)</option>
                  <option value="physical_audit_correction">Stock Ginati Me Galti (Physical Audit)</option>
                </select>
              </div>

              <div className="pt-2 flex items-center justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setSelectedItem(null)}
                  disabled={isSubmitting}
                  className="py-2 px-3.5 text-xs font-semibold text-dukaan-muted hover:text-dukaan-text rounded-xl border border-dukaan-border"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex items-center gap-1.5 py-2 px-4 bg-dukaan-primary hover:bg-dukaan-primaryDark text-white font-bold text-xs rounded-xl shadow-xs disabled:opacity-50"
                >
                  {isSubmitting && <Loader2 className="w-3 h-3 animate-spin" />}
                  <span>Save Karein (सुरक्षित करें)</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
