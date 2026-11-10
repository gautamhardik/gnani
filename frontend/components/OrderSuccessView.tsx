"use client";

import React from "react";
import { Order } from "@/types/api";
import { CheckCircle, Clock, ArrowRight, MessageSquare } from "lucide-react";

interface OrderSuccessViewProps {
  order: Order;
  onNewOrder: () => void;
  onViewChatHistory?: () => void;
}

export function OrderSuccessView({ order, onNewOrder, onViewChatHistory }: OrderSuccessViewProps) {
  return (
    <div className="p-6 flex flex-col items-center text-center animate-in fade-in duration-300">
      <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center mb-4 shadow-warm">
        <CheckCircle className="w-8 h-8" aria-hidden="true" />
      </div>

      <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 mb-2">
        <Clock className="w-3.5 h-3.5" aria-hidden="true" />
        <span>Pending Shopkeeper Approval</span>
      </div>

      <h2 className="text-xl font-bold text-dukaan-text">
        Order Safalta Se Bhej Diya Gaya!
      </h2>
      <p className="text-xs text-dukaan-muted mt-1 max-w-xs">
        Order ID: <span className="font-mono font-bold text-dukaan-text">{order.order_id}</span>
      </p>

      {/* Summary card */}
      <div className="w-full bg-dukaan-card border border-dukaan-border rounded-xl p-4 my-6 text-left shadow-warm">
        <div className="text-xs font-bold text-dukaan-muted uppercase tracking-wider mb-2 border-b border-dukaan-border pb-1.5">
          Order Details
        </div>
        <div className="divide-y divide-dukaan-border/60">
          {order.items.map((it) => (
            <div key={it.item_id} className="py-2 flex items-center justify-between text-xs">
              <span className="font-medium text-dukaan-text">
                {it.product_name_snapshot} ({it.quantity} {it.unit})
              </span>
              <span className="font-bold text-dukaan-text">₹{Number(it.subtotal || 0).toFixed(2)}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 pt-2.5 border-t border-dukaan-border flex items-center justify-between text-sm">
          <span className="font-semibold text-dukaan-text">Kul Rashi:</span>
          <span className="font-extrabold text-dukaan-primaryDark">
            ₹{Number(order.total_amount || 0).toFixed(2)}
          </span>
        </div>
      </div>

      <div className="text-xs text-dukaan-muted bg-stone-100 border border-stone-200 rounded-xl p-3 max-w-sm mb-6 leading-relaxed">
        Everyday Needs General Store aapka saaman check karke accept karega. Kirana dukaan par saaman taiyaar milenge.
      </div>

      <div className="flex flex-col sm:flex-row items-center gap-3 w-full max-w-xs">
        {onViewChatHistory && (
          <button
            onClick={onViewChatHistory}
            className="w-full inline-flex items-center justify-center gap-2 bg-dukaan-card border border-dukaan-border hover:bg-stone-50 text-dukaan-text text-sm font-semibold px-4 py-3 rounded-xl shadow-xs transition-all"
          >
            <MessageSquare className="w-4 h-4 text-dukaan-primary" aria-hidden="true" />
            <span>Chat History Dekhein</span>
          </button>
        )}
        <button
          onClick={onNewOrder}
          className="w-full inline-flex items-center justify-center gap-2 bg-dukaan-primary hover:bg-dukaan-primaryDark text-white text-sm font-semibold px-6 py-3 rounded-xl shadow-warm transition-all"
        >
          <span>Naya Order</span>
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
