"use client";

import React from "react";
import { Store } from "@/types/api";
import { Mic, Clock, MapPin, Sparkles, ArrowRight } from "lucide-react";

interface StoreHomeViewProps {
  store: Store | null;
  onStartOrdering: () => void;
  cartCount: number;
  onViewCart: () => void;
}

export function StoreHomeView({
  store,
  onStartOrdering,
  cartCount,
  onViewCart,
}: StoreHomeViewProps) {
  const storeName = store?.store_name || "Everyday Needs General Store";
  const isOpen = store?.is_open ?? true;

  const examplePhrases = [
    { hi: "दो पैकेट Maggi और एक किलो आटा देना", en: "Do packet Maggi aur ek kilo Aashirvaad aata dena" },
    { hi: "आधा किलो चीनी और अमूल दूध 500ml", en: "Aadha kilo cheeni aur Amul doodh dena" },
    { hi: "फॉर्च्यून रिफाइंड तेल का क्या भाव है?", en: "Fortune tel kitne ka hai?" },
  ];

  return (
    <div className="p-4 space-y-4 animate-in fade-in duration-200">
      {/* Hero Welcome Card */}
      <div className="bg-gradient-to-br from-amber-500/10 via-orange-500/5 to-white/80 border border-dukaan-border/80 rounded-2xl p-5 shadow-warm backdrop-blur-sm">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-dukaan-primary flex items-center gap-1">
            <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Voice-First Neighbourhood Kirana</span>
          </span>
        </div>
        <h2 className="text-xl font-bold text-dukaan-text leading-tight tracking-tight font-heading">
          Namaste! {storeName} par aapka swagat hai.
        </h2>
        <p className="text-xs text-dukaan-muted mt-1.5 leading-relaxed">
          Type karne ki zaroorat nahi hai. Seedha Hindi ya Hinglish mein bol kar grocery order karein.
        </p>

        {/* Store Metadata Status Pills */}
        <div className="flex flex-wrap items-center gap-2 mt-4 text-xs">
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full font-semibold border ${
              isOpen
                ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                : "bg-red-50 text-red-800 border-red-200"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${isOpen ? "bg-emerald-500 animate-pulse" : "bg-red-500"}`}
              aria-hidden="true"
            />
            {isOpen ? "Abhi Khuli Hai (Open)" : "Band Hai (Closed)"}
          </span>

          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/80 border border-dukaan-border/80 text-dukaan-muted text-xs shadow-xs">
            <Clock className="w-3.5 h-3.5 text-stone-400" aria-hidden="true" />
            <span>{store?.opening_time || "8 AM"} - {store?.closing_time || "10 PM"}</span>
          </span>

          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/80 border border-dukaan-border/80 text-dukaan-muted text-xs shadow-xs">
            <MapPin className="w-3.5 h-3.5 text-stone-400" aria-hidden="true" />
            <span>Main Market, Bharat</span>
          </span>
        </div>
      </div>

      {/* Primary Action Card */}
      <div className="bg-white/85 border border-dukaan-border/80 rounded-2xl p-5 shadow-warm text-center space-y-4 backdrop-blur-sm">
        <div className="w-16 h-16 mx-auto rounded-full bg-gradient-to-tr from-orange-100 to-amber-50 border border-orange-200/80 flex items-center justify-center text-dukaan-primary shadow-xs transition-transform active:scale-95">
          <Mic className="w-8 h-8 text-dukaan-primary" aria-hidden="true" />
        </div>

        <div>
          <h3 className="text-base font-bold text-dukaan-text font-heading">Bol Kar Order Karein</h3>
          <p className="text-xs text-dukaan-muted mt-0.5">
            Gnani Prisma STT aur Timbre TTS se direct connected
          </p>
        </div>

        <button
          type="button"
          onClick={onStartOrdering}
          className="w-full py-3.5 px-6 rounded-xl bg-dukaan-primary hover:bg-dukaan-primaryDark text-white font-bold text-sm shadow-warm flex items-center justify-center gap-2.5 transition-all transform active:scale-[0.98]"
        >
          <Mic className="w-5 h-5 fill-white" aria-hidden="true" />
          <span>Awaaz Se Order Shuru Karein</span>
          <ArrowRight className="w-4 h-4 ml-1" aria-hidden="true" />
        </button>

        {cartCount > 0 && (
          <button
            type="button"
            onClick={onViewCart}
            className="w-full py-2.5 px-4 rounded-xl bg-stone-50/80 hover:bg-stone-100 text-dukaan-text border border-dukaan-border font-semibold text-xs transition-colors flex items-center justify-center gap-2 active:scale-[0.99]"
          >
            <span>Cart Dekhein ({cartCount} Items)</span>
          </button>
        )}
      </div>

      {/* Spoken Utterance Examples */}
      <div className="bg-white/85 border border-dukaan-border/80 rounded-2xl p-4 shadow-warm backdrop-blur-sm">
        <div className="flex items-center gap-2 text-xs font-bold text-dukaan-muted uppercase tracking-wider mb-2.5">
          <Sparkles className="w-4 h-4 text-dukaan-primary" aria-hidden="true" />
          <span>Aap Aise Bol Sakte Hain:</span>
        </div>
        <div className="space-y-2">
          {examplePhrases.map((ex, i) => (
            <button
              key={i}
              type="button"
              onClick={onStartOrdering}
              className="w-full text-left bg-stone-50/70 hover:bg-orange-50/60 border border-dukaan-border/70 hover:border-orange-200 rounded-xl p-2.5 text-xs transition-colors group cursor-pointer"
            >
              <div className="font-medium text-dukaan-text group-hover:text-dukaan-primary transition-colors">
                &ldquo;{ex.hi}&rdquo;
              </div>
              <div className="text-[11px] text-dukaan-muted mt-0.5">{ex.en}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
