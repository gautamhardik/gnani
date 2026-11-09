"use client";

import React, { useState } from "react";
import { CartItem } from "@/types/api";
import { CheckCircle2, ShieldCheck, AlertCircle, Loader2, ArrowLeft } from "lucide-react";

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  items: CartItem[];
  totalAmount: number;
  onConfirmOrder: () => Promise<void>;
}

export function ConfirmationModal({
  isOpen,
  onClose,
  items,
  totalAmount,
  onConfirmOrder,
}: ConfirmationModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await onConfirmOrder();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(
        msg || "Order submit karne mein dikkat aayi. Kripya dobara koshish karein."
      );
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-xs p-0 sm:p-4 animate-in fade-in duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-modal-title"
    >
      <div className="w-full max-w-md bg-dukaan-card rounded-t-2xl sm:rounded-2xl border border-dukaan-border shadow-floating overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-5 py-4 border-b border-dukaan-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              disabled={isSubmitting}
              className="p-1 text-dukaan-muted hover:text-dukaan-text rounded-lg"
              aria-label="Back to cart"
            >
              <ArrowLeft className="w-5 h-5" aria-hidden="true" />
            </button>
            <h3 id="confirm-modal-title" className="text-base font-bold text-dukaan-text">
              Order Confirmation
            </h3>
          </div>
          <span className="text-xs font-semibold bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
            Review Step
          </span>
        </div>

        {/* Scrollable item list */}
        <div className="p-5 overflow-y-auto space-y-3.5 flex-1">
          <div className="bg-amber-50/60 border border-amber-200/70 rounded-xl p-3 flex items-start gap-2.5 text-xs text-amber-900 leading-relaxed">
            <ShieldCheck className="w-4 h-4 text-amber-700 shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <strong>DukaanSaathi Policy:</strong> Yeh order Sharma General Store ke paas jaayega. Shopkeeper ke accept karne ke baad hi inventory book hogi.
            </div>
          </div>

          {errorMessage && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-3 flex items-start gap-2 text-xs text-red-700">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div>
            <h4 className="text-xs font-bold text-dukaan-muted uppercase tracking-wider mb-2">
              Itemized Order ({items.length})
            </h4>
            <div className="divide-y divide-dukaan-border border border-dukaan-border rounded-xl overflow-hidden bg-dukaan-canvas">
              {items.map((it) => (
                <div key={it.product_id} className="p-3 flex items-center justify-between text-xs">
                  <div>
                    <div className="font-semibold text-dukaan-text">{it.name}</div>
                    <div className="text-dukaan-muted">
                      {it.quantity} {it.unit} × ₹{Number(it.unit_price || 0).toFixed(2)}
                    </div>
                  </div>
                  <div className="font-bold text-dukaan-text">
                    ₹{Number(it.subtotal || 0).toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-2 border-t border-dukaan-border flex items-center justify-between">
            <span className="text-sm font-semibold text-dukaan-text">Kul Rashi (Total):</span>
            <span className="text-lg font-extrabold text-dukaan-primaryDark">
              ₹{Number(totalAmount || 0).toFixed(2)}
            </span>
          </div>
        </div>

        {/* Footer actions */}
        <div className="p-4 bg-dukaan-canvas border-t border-dukaan-border flex items-center gap-3">
          <button
            type="button"
            disabled={isSubmitting}
            onClick={onClose}
            className="flex-1 py-2.5 px-4 text-sm font-semibold text-dukaan-muted hover:text-dukaan-text bg-dukaan-card border border-dukaan-border rounded-xl transition-colors"
          >
            Badlaav Karein
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            onClick={handleSubmit}
            className="flex-1 py-2.5 px-4 text-sm font-semibold text-white bg-dukaan-primary hover:bg-dukaan-primaryDark rounded-xl shadow-warm flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                <span>Bhej rahe hain...</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                <span>Haan, Order Bhejo</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
