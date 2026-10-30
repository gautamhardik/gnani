"use client";

import React, { useState } from "react";
import { CartItem } from "@/types/api";
import { Plus, Minus, Trash2, ShoppingBag, ArrowRight, Loader2 } from "lucide-react";

interface CartViewProps {
  items: CartItem[];
  totalAmount: number;
  onUpdateQuantity: (productId: string, quantity: number) => Promise<void>;
  onRemoveItem: (productId: string) => Promise<void>;
  onProceedToConfirm: () => void;
  onStartVoice: () => void;
}

export function CartView({
  items,
  totalAmount,
  onUpdateQuantity,
  onRemoveItem,
  onProceedToConfirm,
  onStartVoice,
}: CartViewProps) {
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const handleQtyChange = async (productId: string, newQty: number) => {
    setUpdatingId(productId);
    try {
      if (newQty <= 0) {
        await onRemoveItem(productId);
      } else {
        await onUpdateQuantity(productId, newQty);
      }
    } finally {
      setUpdatingId(null);
    }
  };

  const handleRemove = async (productId: string) => {
    setUpdatingId(productId);
    try {
      await onRemoveItem(productId);
    } finally {
      setUpdatingId(null);
    }
  };

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center min-h-[350px]">
        <div className="w-16 h-16 rounded-2xl bg-dukaan-canvas border border-dukaan-border flex items-center justify-center mb-4 text-dukaan-muted">
          <ShoppingBag className="w-8 h-8 text-dukaan-muted" aria-hidden="true" />
        </div>
        <h3 className="text-base font-bold text-dukaan-text">Aapki Cart Khali Hai</h3>
        <p className="text-xs text-dukaan-muted mt-1.5 max-w-xs leading-relaxed">
          DukaanSaathi se bol kar saaman mangwayein. Mic dabayein aur boliye jaise shopkeeper se baat karte hain.
        </p>
        <button
          onClick={onStartVoice}
          className="mt-5 inline-flex items-center gap-2 bg-dukaan-primary hover:bg-dukaan-primaryDark text-white text-sm font-semibold px-5 py-2.5 rounded-xl shadow-warm transition-all"
        >
          <span>Bol Kar Mangwayein</span>
          <ArrowRight className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between border-b border-dukaan-border pb-2">
        <h2 className="text-sm font-bold text-dukaan-text uppercase tracking-wider">
          Aapka Saaman ({items.length} Items)
        </h2>
        <span className="text-xs text-dukaan-muted">Authoritative Server Rates</span>
      </div>

      <div className="space-y-3" role="list" aria-label="Cart Items">
        {items.map((item) => {
          const isBusy = updatingId === item.product_id;

          return (
            <div
              key={item.product_id}
              role="listitem"
              className="bg-dukaan-card border border-dukaan-border rounded-xl p-3 shadow-warm flex items-center justify-between gap-3"
            >
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-semibold text-dukaan-text truncate">
                  {item.name}
                </h4>
                <div className="text-xs text-dukaan-muted mt-0.5 flex items-center gap-2">
                  <span>
                    ₹{item.unit_price.toFixed(2)} / {item.unit}
                  </span>
                  {item.requested_quantity && (
                    <span className="text-[10px] bg-stone-100 text-stone-600 px-1.5 py-0.5 rounded">
                      Bole the: {item.requested_quantity} {item.requested_unit}
                    </span>
                  )}
                </div>
                <div className="text-xs font-bold text-dukaan-primaryDark mt-1">
                  Subtotal: ₹{item.subtotal.toFixed(2)}
                </div>
              </div>

              {/* Quantity steppers & remove */}
              <div className="flex items-center gap-2">
                <div className="flex items-center bg-dukaan-canvas border border-dukaan-border rounded-lg p-0.5 shadow-xs">
                  <button
                    disabled={isBusy}
                    onClick={() => handleQtyChange(item.product_id, item.quantity - 1)}
                    className="w-7 h-7 flex items-center justify-center text-dukaan-text hover:bg-stone-200 rounded disabled:opacity-40 transition-colors"
                    aria-label={`Decrease quantity of ${item.name}`}
                  >
                    <Minus className="w-3.5 h-3.5" aria-hidden="true" />
                  </button>

                  <span className="w-8 text-center text-xs font-bold text-dukaan-text">
                    {isBusy ? (
                      <Loader2 className="w-3 h-3 animate-spin mx-auto text-dukaan-muted" />
                    ) : (
                      item.quantity
                    )}
                  </span>

                  <button
                    disabled={isBusy}
                    onClick={() => handleQtyChange(item.product_id, item.quantity + 1)}
                    className="w-7 h-7 flex items-center justify-center text-dukaan-text hover:bg-stone-200 rounded disabled:opacity-40 transition-colors"
                    aria-label={`Increase quantity of ${item.name}`}
                  >
                    <Plus className="w-3.5 h-3.5" aria-hidden="true" />
                  </button>
                </div>

                <button
                  disabled={isBusy}
                  onClick={() => handleRemove(item.product_id)}
                  className="p-1.5 text-stone-400 hover:text-dukaan-error hover:bg-red-50 rounded-lg transition-colors"
                  aria-label={`Remove ${item.name} from cart`}
                >
                  <Trash2 className="w-4 h-4" aria-hidden="true" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bill summary & checkout CTA */}
      <div className="bg-dukaan-card border border-dukaan-border rounded-xl p-4 shadow-warm mt-4">
        <div className="flex items-center justify-between text-sm text-dukaan-muted mb-1">
          <span>Items Total ({items.length})</span>
          <span>₹{totalAmount.toFixed(2)}</span>
        </div>
        <div className="flex items-center justify-between text-sm text-dukaan-muted mb-3">
          <span>Dukaan Delivery / Packaging</span>
          <span className="text-dukaan-success font-medium">Free</span>
        </div>
        <div className="border-t border-dukaan-border pt-2.5 flex items-center justify-between">
          <div>
            <div className="text-xs text-dukaan-muted">Kul Rashi (Grand Total)</div>
            <div className="text-lg font-bold text-dukaan-text">
              ₹{totalAmount.toFixed(2)}
            </div>
          </div>
          <button
            onClick={onProceedToConfirm}
            className="inline-flex items-center gap-2 bg-dukaan-primary hover:bg-dukaan-primaryDark text-white text-sm font-semibold px-5 py-2.5 rounded-xl shadow-warm transition-all"
          >
            <span>Order Confirm Karein</span>
            <ArrowRight className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );
}

