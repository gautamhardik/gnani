"use client";

import React, { useState } from "react";
import {
  Check,
  X,
  PackageCheck,
  Truck,
  AlertCircle,
  Loader2,
  ChevronRight,
} from "lucide-react";
import { Order } from "@/types/api";
import {
  acceptOrder,
  rejectOrder,
  updateOrderStatus,
} from "@/lib/merchantApi";

interface OrdersTabProps {
  orders: Order[];
  selectedStatus: string;
  onSelectStatus: (status: string) => void;
  onRefresh: () => void;
  selectedOrder: Order | null;
  onSelectOrder: (order: Order | null) => void;
}

export function OrdersTab({
  orders,
  selectedStatus,
  onSelectStatus,
  onRefresh,
  selectedOrder,
  onSelectOrder,
}: OrdersTabProps) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  // Rejection modal state
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  // Confirmation modal state
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    onConfirm: () => Promise<void>;
  }>({
    isOpen: false,
    title: "",
    description: "",
    onConfirm: async () => {},
  });

  const filterTabs = [
    { id: "all", label: "Sabhi (All)" },
    { id: "pending", label: "Pending (लंबित)" },
    { id: "accepted", label: "Accepted (स्वीकृत)" },
    { id: "preparing", label: "Preparing (तैयार हो रहा)" },
    { id: "ready", label: "Ready (तैयार)" },
    { id: "completed", label: "Completed (पूरा)" },
    { id: "rejected", label: "Rejected (अस्वीकृत)" },
    { id: "cancelled", label: "Cancelled (रद्द)" },
  ];

  const statusBadges: Record<string, { bg: string; text: string; label: string }> = {
    pending: { bg: "bg-amber-100", text: "text-amber-800", label: "Pending" },
    accepted: { bg: "bg-blue-100", text: "text-blue-800", label: "Accepted" },
    preparing: { bg: "bg-purple-100", text: "text-purple-800", label: "Preparing" },
    ready: { bg: "bg-teal-100", text: "text-teal-800", label: "Ready" },
    completed: { bg: "bg-emerald-100", text: "text-emerald-800", label: "Completed" },
    rejected: { bg: "bg-rose-100", text: "text-rose-800", label: "Rejected" },
    cancelled: { bg: "bg-stone-200", text: "text-stone-700", label: "Cancelled" },
  };

  const handleAccept = (order: Order) => {
    setConfirmDialog({
      isOpen: true,
      title: "Order Sweekar Karein? (Accept Order)",
      description: `Order #${order.order_id} sweekar karne par dukan ke live inventory se saman ghataya jayega. Kya aap aage badhana chahte hain?`,
      onConfirm: async () => {
        setIsProcessing(true);
        setActionError(null);
        try {
          const updated = await acceptOrder(order.order_id);
          onSelectOrder(updated);
          onRefresh();
          setConfirmDialog((prev) => ({ ...prev, isOpen: false }));
        } catch (err: unknown) {
          setActionError(err instanceof Error ? err.message : "Acceptance failed");
        } finally {
          setIsProcessing(false);
        }
      },
    });
  };

  const handleOpenReject = (order: Order) => {
    onSelectOrder(order);
    setRejectReason("Dukan par stock uplabdh nahi hai");
    setShowRejectModal(true);
    setActionError(null);
  };

  const handleConfirmReject = async () => {
    if (!selectedOrder) return;
    setIsProcessing(true);
    setActionError(null);
    try {
      const updated = await rejectOrder(selectedOrder.order_id, rejectReason);
      onSelectOrder(updated);
      setShowRejectModal(false);
      onRefresh();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Rejection failed");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleStatusTransition = (
    order: Order,
    nextStatus: "preparing" | "ready" | "completed" | "cancelled"
  ) => {
    const titles: Record<string, string> = {
      preparing: "Order Taiyari Shuru Karein (Mark as Preparing)?",
      ready: "Order Taiyar Hai (Mark as Ready for Pickup)?",
      completed: "Order Pura Karein (Mark as Completed)?",
      cancelled: "Order Radd Karein (Cancel & Restock Inventory)?",
    };

    const descriptions: Record<string, string> = {
      preparing: `Order #${order.order_id} packing stage me move kiya jayega.`,
      ready: `Order #${order.order_id} grahak ke lene ke liye counter par ready hai.`,
      completed: `Order #${order.order_id} grahak ko de diya gaya hai aur transaction complete ho gayi hai.`,
      cancelled: `Order #${order.order_id} cancel karne par deduct hua saman dukan inventory me vapis jod diya jayega.`,
    };

    setConfirmDialog({
      isOpen: true,
      title: titles[nextStatus],
      description: descriptions[nextStatus],
      onConfirm: async () => {
        setIsProcessing(true);
        setActionError(null);
        try {
          const updated = await updateOrderStatus(order.order_id, nextStatus);
          onSelectOrder(updated);
          onRefresh();
          setConfirmDialog((prev) => ({ ...prev, isOpen: false }));
        } catch (err: unknown) {
          setActionError(err instanceof Error ? err.message : "Status transition failed");
        } finally {
          setIsProcessing(false);
        }
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Status Filter Bar */}
      <div className="bg-dukaan-card border border-dukaan-border rounded-2xl p-2 shadow-xs overflow-x-auto">
        <div className="flex items-center gap-1 min-w-max">
          {filterTabs.map((tab) => {
            const isActive = selectedStatus === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onSelectStatus(tab.id)}
                className={`text-xs font-semibold px-3 py-2 rounded-xl transition-all ${
                  isActive
                    ? "bg-dukaan-primary text-white shadow-warm"
                    : "text-dukaan-muted hover:text-dukaan-text hover:bg-dukaan-canvas"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Action Error Alert */}
      {actionError && (
        <div
          role="alert"
          className="p-3.5 rounded-xl bg-dukaan-errorBg border border-dukaan-error/30 flex items-center justify-between text-xs text-dukaan-error"
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{actionError}</span>
          </div>
          <button
            onClick={() => setActionError(null)}
            className="text-dukaan-error font-bold text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* Orders List / Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Orders Table (2 cols on large) */}
        <div className="lg:col-span-2 bg-dukaan-card border border-dukaan-border rounded-2xl shadow-warm overflow-hidden">
          <div className="p-4 sm:p-5 border-b border-dukaan-border flex items-center justify-between">
            <h2 className="text-sm font-bold text-dukaan-text">
              Orders Suchi ({orders.length})
            </h2>
            <span className="text-xs text-dukaan-muted">
              Live updates active
            </span>
          </div>

          {orders.length === 0 ? (
            <div className="p-10 text-center text-xs text-dukaan-muted">
              Is filter ke antargat koi order nahi mila.
            </div>
          ) : (
            <div
              tabIndex={0}
              role="region"
              aria-label="Merchant orders table"
              className="overflow-x-auto"
            >
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-dukaan-canvas text-dukaan-muted uppercase text-[10px] font-bold tracking-wider border-b border-dukaan-border">
                  <tr>
                    <th className="py-3 px-4">Order ID</th>
                    <th className="py-3 px-4">Samay</th>
                    <th className="py-3 px-4">Saman Count</th>
                    <th className="py-3 px-4">Kul Rakam</th>
                    <th className="py-3 px-4">Sthiti (Status)</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dukaan-border/60">
                  {orders.map((order) => {
                    const badge = statusBadges[order.status] || {
                      bg: "bg-stone-100",
                      text: "text-stone-700",
                      label: order.status,
                    };
                    const isSelected = selectedOrder?.order_id === order.order_id;
                    const dateStr = new Date(order.created_at).toLocaleTimeString("en-IN", {
                      hour: "2-digit",
                      minute: "2-digit",
                    });

                    return (
                      <tr
                        key={order.order_id}
                        onClick={() => onSelectOrder(order)}
                        className={`hover:bg-dukaan-canvas/60 transition-colors cursor-pointer ${
                          isSelected ? "bg-dukaan-primary/5" : ""
                        }`}
                      >
                        <td className="py-3.5 px-4 font-mono font-bold text-dukaan-text">
                          #{order.order_id}
                        </td>
                        <td className="py-3.5 px-4 text-dukaan-muted whitespace-nowrap">
                          {dateStr}
                        </td>
                        <td className="py-3.5 px-4 text-dukaan-text font-medium">
                          {order.items?.length || 0} items
                        </td>
                        <td className="py-3.5 px-4 font-mono font-bold text-dukaan-text whitespace-nowrap">
                          ₹{Number(order.total_amount).toFixed(2)}
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${badge.bg} ${badge.text}`}
                          >
                            {badge.label}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right whitespace-nowrap">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectOrder(order);
                            }}
                            className="inline-flex items-center gap-1 text-[11px] font-semibold text-dukaan-primary hover:text-dukaan-primaryDark"
                          >
                            <span>Dekhein</span>
                            <ChevronRight className="w-3.5 h-3.5" />
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

        {/* Selected Order Drill-Down Detail Drawer (1 col) */}
        <div className="bg-dukaan-card border border-dukaan-border rounded-2xl p-5 shadow-warm flex flex-col h-fit">
          <div className="border-b border-dukaan-border pb-4 mb-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-dukaan-text">
                Order Vivaran (Detail)
              </h3>
              {selectedOrder && (
                <span
                  className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                    statusBadges[selectedOrder.status]?.bg
                  } ${statusBadges[selectedOrder.status]?.text}`}
                >
                  {statusBadges[selectedOrder.status]?.label}
                </span>
              )}
            </div>
            {selectedOrder ? (
              <p className="text-xs text-dukaan-muted mt-1 font-mono">
                ID: #{selectedOrder.order_id}
              </p>
            ) : (
              <p className="text-xs text-dukaan-muted mt-1">
                Kripya table se order select karein
              </p>
            )}
          </div>

          {!selectedOrder ? (
            <div className="text-center py-12 text-xs text-dukaan-muted">
              Vivaran dekhne aur action lene ke liye kripya kisi order par click karein.
            </div>
          ) : (
            <div className="space-y-4 flex-1">
              {/* Items List */}
              <div>
                <span className="text-[11px] font-bold text-dukaan-muted uppercase tracking-wider block mb-2">
                  Order Items ({selectedOrder.items?.length || 0})
                </span>
                <div className="max-h-56 overflow-y-auto divide-y divide-dukaan-border/50 border border-dukaan-border rounded-xl p-2 bg-dukaan-canvas/40">
                  {selectedOrder.items?.map((item, idx) => (
                    <div key={idx} className="py-2 flex items-center justify-between text-xs">
                      <div>
                        <p className="font-semibold text-dukaan-text">
                          {item.product_name_snapshot}
                        </p>
                        <p className="text-[11px] text-dukaan-muted">
                          {item.quantity} {item.unit} × ₹{Number(item.unit_price).toFixed(2)}
                        </p>
                      </div>
                      <span className="font-mono font-bold text-dukaan-text">
                        ₹{Number(item.subtotal).toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Total Amount */}
              <div className="bg-dukaan-canvas p-3 rounded-xl flex items-center justify-between">
                <span className="text-xs font-bold text-dukaan-text">
                  Kul Rakam (Total):
                </span>
                <span className="text-sm font-extrabold text-dukaan-primary font-mono">
                  ₹{Number(selectedOrder.total_amount).toFixed(2)}
                </span>
              </div>

              {/* Rejection / Cancellation Notes */}
              {selectedOrder.rejection_reason && (
                <div className="p-3 bg-dukaan-canvas rounded-xl text-xs text-dukaan-muted">
                  <span className="font-semibold block text-dukaan-text">
                    Tippani (Note / Reason):
                  </span>
                  {selectedOrder.rejection_reason}
                </div>
              )}

              {/* Status Action Buttons */}
              <div className="pt-2 space-y-2">
                {selectedOrder.status === "pending" && (
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      onClick={() => handleAccept(selectedOrder)}
                      disabled={isProcessing}
                      className="flex items-center justify-center gap-1.5 py-2.5 px-3 bg-dukaan-success hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors disabled:opacity-50"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>Accept (स्वीकार)</span>
                    </button>
                    <button
                      onClick={() => handleOpenReject(selectedOrder)}
                      disabled={isProcessing}
                      className="flex items-center justify-center gap-1.5 py-2.5 px-3 bg-dukaan-error hover:bg-rose-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors disabled:opacity-50"
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>Reject (अस्वीकार)</span>
                    </button>
                  </div>
                )}

                {selectedOrder.status === "accepted" && (
                  <div className="space-y-2">
                    <button
                      onClick={() => handleStatusTransition(selectedOrder, "preparing")}
                      disabled={isProcessing}
                      className="w-full flex items-center justify-center gap-1.5 py-2.5 px-3 bg-dukaan-primary hover:bg-dukaan-primaryDark text-white font-bold text-xs rounded-xl shadow-xs transition-colors disabled:opacity-50"
                    >
                      <PackageCheck className="w-3.5 h-3.5" />
                      <span>Taiyari Shuru Karein (Mark Preparing)</span>
                    </button>
                    <button
                      onClick={() => handleStatusTransition(selectedOrder, "cancelled")}
                      disabled={isProcessing}
                      className="w-full flex items-center justify-center gap-1 text-[11px] font-semibold text-dukaan-error hover:underline py-1"
                    >
                      <span>Order Cancel Karein (Restock Stock)</span>
                    </button>
                  </div>
                )}

                {selectedOrder.status === "preparing" && (
                  <div className="space-y-2">
                    <button
                      onClick={() => handleStatusTransition(selectedOrder, "ready")}
                      disabled={isProcessing}
                      className="w-full flex items-center justify-center gap-1.5 py-2.5 px-3 bg-teal-600 hover:bg-teal-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors disabled:opacity-50"
                    >
                      <Truck className="w-3.5 h-3.5" />
                      <span>Pickup Hetu Taiyar (Mark Ready)</span>
                    </button>
                    <button
                      onClick={() => handleStatusTransition(selectedOrder, "cancelled")}
                      disabled={isProcessing}
                      className="w-full flex items-center justify-center gap-1 text-[11px] font-semibold text-dukaan-error hover:underline py-1"
                    >
                      <span>Order Cancel Karein (Restock Stock)</span>
                    </button>
                  </div>
                )}

                {selectedOrder.status === "ready" && (
                  <button
                    onClick={() => handleStatusTransition(selectedOrder, "completed")}
                    disabled={isProcessing}
                    className="w-full flex items-center justify-center gap-1.5 py-2.5 px-3 bg-dukaan-success hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-xs transition-colors disabled:opacity-50"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Order Diya Gaya (Mark Completed)</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Confirmation Dialog Modal */}
      {confirmDialog.isOpen && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4"
        >
          <div className="bg-dukaan-card border border-dukaan-border rounded-2xl p-6 max-w-sm w-full shadow-floating animate-in fade-in zoom-in-95">
            <h3 className="text-sm font-bold text-dukaan-text mb-2">
              {confirmDialog.title}
            </h3>
            <p className="text-xs text-dukaan-muted leading-relaxed mb-6">
              {confirmDialog.description}
            </p>
            <div className="flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setConfirmDialog((prev) => ({ ...prev, isOpen: false }))}
                disabled={isProcessing}
                className="py-2 px-3.5 text-xs font-semibold text-dukaan-muted hover:text-dukaan-text rounded-xl border border-dukaan-border"
              >
                Radd (Cancel)
              </button>
              <button
                type="button"
                onClick={confirmDialog.onConfirm}
                disabled={isProcessing}
                className="flex items-center gap-1.5 py-2 px-4 bg-dukaan-primary hover:bg-dukaan-primaryDark text-white font-bold text-xs rounded-xl shadow-xs disabled:opacity-50"
              >
                {isProcessing && <Loader2 className="w-3 h-3 animate-spin" />}
                <span>Haan, Aage Badhein (Proceed)</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rejection Modal */}
      {showRejectModal && selectedOrder && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4"
        >
          <div className="bg-dukaan-card border border-dukaan-border rounded-2xl p-6 max-w-sm w-full shadow-floating animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-dukaan-text">
                Order Asweekar Karein (Reject Order)
              </h3>
              <button
                onClick={() => setShowRejectModal(false)}
                className="text-dukaan-muted hover:text-dukaan-text text-sm"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-dukaan-muted mb-4">
              Order #{selectedOrder.order_id} ko reject karne ka karan chunein ya likhein. Isse inventory se koi saman deduct nahi hoga.
            </p>
            <div className="mb-4">
              <label
                htmlFor="reject-reason"
                className="block text-xs font-semibold text-dukaan-text mb-1"
              >
                Karan (Reason):
              </label>
              <input
                id="reject-reason"
                type="text"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="e.g. Stock khatam ho gaya"
                className="w-full py-2 px-3 text-xs bg-dukaan-canvas border border-dukaan-border rounded-xl focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30"
              />
            </div>
            <div className="flex items-center justify-end gap-2.5">
              <button
                type="button"
                onClick={() => setShowRejectModal(false)}
                disabled={isProcessing}
                className="py-2 px-3.5 text-xs font-semibold text-dukaan-muted hover:text-dukaan-text rounded-xl border border-dukaan-border"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmReject}
                disabled={isProcessing}
                className="flex items-center gap-1.5 py-2 px-4 bg-dukaan-error hover:bg-rose-700 text-white font-bold text-xs rounded-xl shadow-xs disabled:opacity-50"
              >
                {isProcessing && <Loader2 className="w-3 h-3 animate-spin" />}
                <span>Reject Karein</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
