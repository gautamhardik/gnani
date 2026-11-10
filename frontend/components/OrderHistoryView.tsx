"use client";

import React, { useEffect, useState } from "react";
import { Order } from "@/types/api";
import { getCustomerOrder } from "@/lib/api";
import { Package, ShoppingBag, MessageSquare, ChevronDown, ChevronUp } from "lucide-react";

interface OrderHistoryViewProps {
  onBackToOrder: () => void;
  onSelectOrder?: (order: Order) => void;
}

export function OrderHistoryView({ onBackToOrder }: OrderHistoryViewProps) {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedChatIds, setExpandedChatIds] = useState<Record<string, boolean>>({});

  const toggleExpand = (orderId: string) => {
    setExpandedChatIds((prev) => ({
      ...prev,
      [orderId]: !prev[orderId],
    }));
  };

  useEffect(() => {
    async function loadPastOrders() {
      if (typeof window === "undefined") return;
      try {
        const stored = localStorage.getItem("dukaansaathi_order_history");
        if (stored) {
          const parsed: Array<{ order_id: string; session_id: string }> = JSON.parse(stored);
          const fetched: Order[] = [];
          for (const item of parsed.slice(-10).reverse()) {
            try {
              const ord = await getCustomerOrder(item.order_id, item.session_id);
              if (ord) fetched.push(ord);
            } catch {
              // Ignore single lookup failure
            }
          }
          setOrders(fetched);
        }
      } catch (err) {
        console.error("Failed to load order history:", err);
      } finally {
        setLoading(false);
      }
    }
    loadPastOrders();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <span className="bg-emerald-100 text-emerald-800 text-xs px-2 py-0.5 rounded-full font-medium">Completed</span>;
      case "accepted":
      case "preparing":
        return <span className="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full font-medium">Preparing</span>;
      case "ready":
        return <span className="bg-purple-100 text-purple-800 text-xs px-2 py-0.5 rounded-full font-medium">Ready</span>;
      case "rejected":
      case "cancelled":
        return <span className="bg-rose-100 text-rose-800 text-xs px-2 py-0.5 rounded-full font-medium">Cancelled</span>;
      default:
        return <span className="bg-amber-100 text-amber-800 text-xs px-2 py-0.5 rounded-full font-medium">Pending</span>;
    }
  };

  return (
    <div className="flex flex-col min-h-[calc(100vh-65px)] max-w-md mx-auto p-4">
      <div className="flex items-center justify-between pb-3 border-b border-dukaan-border mb-4">
        <div>
          <h2 className="text-lg font-bold text-dukaan-text">Aapke Pichle Orders (History)</h2>
          <p className="text-xs text-dukaan-muted">Purane orders aur unka current status</p>
        </div>
        <button
          onClick={onBackToOrder}
          className="text-xs bg-dukaan-primary hover:bg-dukaan-primaryDark text-white font-semibold px-3 py-1.5 rounded-lg transition-colors"
        >
          Naya Order
        </button>
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-sm text-dukaan-muted">
          Orders load ho rahe hain...
        </div>
      ) : orders.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-dukaan-muted">
          <div className="w-14 h-14 rounded-full bg-stone-100 flex items-center justify-center mb-3">
            <ShoppingBag className="w-7 h-7 text-stone-400" />
          </div>
          <p className="text-sm font-semibold text-dukaan-text">Abhi koi purana order nahi hai</p>
          <p className="text-xs text-dukaan-muted mt-1 max-w-xs">
            Jab aap order confirm karenge, yahan unki poori list aur receipt dikhegi.
          </p>
        </div>
      ) : (
        <div className="space-y-3 pb-6">
          {orders.map((ord) => (
            <div
              key={ord.order_id}
              className="bg-dukaan-card border border-dukaan-border rounded-xl p-3.5 shadow-xs"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5 text-xs font-bold text-dukaan-text">
                  <Package className="w-4 h-4 text-dukaan-primary" />
                  <span>Order #{ord.order_id.slice(-6).toUpperCase()}</span>
                </div>
                {getStatusBadge(ord.status)}
              </div>

              <div className="text-xs text-dukaan-muted mb-2">
                {new Date(ord.created_at).toLocaleString([], {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </div>

              <div className="border-t border-stone-100 pt-2 mb-2 space-y-1">
                {ord.items?.map((it) => (
                  <div key={it.item_id} className="flex justify-between text-xs text-dukaan-text">
                    <span>
                      {it.quantity} {it.unit} x {it.product_name_snapshot || it.product_id}
                    </span>
                    <span className="font-semibold text-stone-800">
                      ₹{it.subtotal}
                    </span>
                  </div>
                ))}
              </div>

              <div className="border-t border-dukaan-border pt-2 flex justify-between items-center text-xs">
                <span className="font-semibold text-dukaan-text">Kul Rashi (Total):</span>
                <span className="text-sm font-bold text-dukaan-primary">
                  ₹{ord.total_amount}
                </span>
              </div>

              {/* Chat History Accordion */}
              {ord.conversation_history && ord.conversation_history.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-dashed border-dukaan-border">
                  <button
                    type="button"
                    onClick={() => toggleExpand(ord.order_id)}
                    className="w-full flex items-center justify-between text-xs font-semibold text-stone-700 hover:text-dukaan-primary transition-colors py-1 px-1 rounded-md hover:bg-stone-50"
                  >
                    <span className="flex items-center gap-1.5">
                      <MessageSquare className="w-3.5 h-3.5 text-dukaan-primary" />
                      <span>Chat History ({ord.conversation_history.length} baatein)</span>
                    </span>
                    {expandedChatIds[ord.order_id] ? (
                      <ChevronUp className="w-3.5 h-3.5 text-stone-500" />
                    ) : (
                      <ChevronDown className="w-3.5 h-3.5 text-stone-500" />
                    )}
                  </button>

                  {expandedChatIds[ord.order_id] && (
                    <div className="mt-2 p-2.5 bg-stone-50 rounded-xl border border-stone-200/80 space-y-2 max-h-56 overflow-y-auto">
                      {ord.conversation_history.map((msg, idx) => (
                        <div
                          key={idx}
                          className={`text-xs p-2.5 rounded-xl ${
                            msg.sender === "customer"
                              ? "bg-orange-100 text-orange-950 ml-3 rounded-tr-xs"
                              : "bg-white text-stone-900 mr-3 border border-stone-200/80 rounded-tl-xs shadow-xs"
                          }`}
                        >
                          <div className="flex items-center justify-between text-[10px] font-bold text-stone-500 mb-1">
                            <span>{msg.sender === "customer" ? "Grahak (ग्राहक)" : "दुकान साथी (Sharma Ji)"}</span>
                            {Boolean(msg.timestamp) && <span>{String(msg.timestamp)}</span>}
                          </div>
                          <div className="leading-relaxed whitespace-pre-wrap">{String(msg.text || "")}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
