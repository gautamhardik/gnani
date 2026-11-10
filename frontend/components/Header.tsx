"use client";

import React from "react";
import { Store } from "@/types/api";
import { Store as StoreIcon, ShoppingBag, Clock, History, Mic } from "lucide-react";

interface HeaderProps {
  store: Store | null;
  selectedLanguage: string;
  onLanguageChange: (lang: string) => void;
  cartCount: number;
  activeTab: "home" | "voice" | "cart" | "history";
  onTabChange: (tab: "home" | "voice" | "cart" | "history") => void;
}

export function Header({
  store,
  selectedLanguage,
  onLanguageChange,
  cartCount,
  activeTab,
  onTabChange,
}: HeaderProps) {
  const storeName = store?.store_name || "Everyday Needs General Store";
  const isOpen = store?.is_open ?? true;

  return (
    <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-dukaan-border/80 shadow-warm transition-colors">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-between gap-4">
        {/* Store Brand & Identity */}
        <button
          type="button"
          onClick={() => onTabChange("home")}
          className="flex items-center gap-3 text-left focus:outline-none group cursor-pointer min-w-0 flex-shrink"
          aria-label="Go to Store Home"
        >
          <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-dukaan-primary/10 border border-dukaan-primary/20 flex items-center justify-center text-dukaan-primary font-bold shadow-xs transition-transform group-active:scale-95 flex-shrink-0">
            <StoreIcon className="w-5 h-5 text-dukaan-primary" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm sm:text-base font-bold text-dukaan-text leading-tight tracking-tight font-heading group-hover:text-dukaan-primary transition-colors whitespace-nowrap overflow-hidden text-ellipsis">
              {storeName}
            </h1>
            <div className="flex items-center gap-2 mt-0.5 text-xs text-dukaan-muted">
              <span
                className={`inline-flex items-center gap-1 font-semibold whitespace-nowrap ${
                  isOpen ? "text-dukaan-success" : "text-dukaan-error"
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isOpen ? "bg-dukaan-success animate-pulse" : "bg-dukaan-error"
                  }`}
                  aria-hidden="true"
                />
                {isOpen ? "Dukaan Khuli Hai" : "Band Hai"}
              </span>
              <span className="opacity-40">•</span>
              <span className="flex items-center gap-1 font-medium whitespace-nowrap">
                <Clock className="w-3 h-3 text-stone-400" aria-hidden="true" />
                <span>{store?.opening_time || "8 AM"} - {store?.closing_time || "10 PM"}</span>
              </span>
            </div>
          </div>
        </button>

        {/* Action Controls & Navigation */}
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          {/* Language preference dropdown */}
          <div className="relative">
            <label htmlFor="language-select" className="sr-only">
              Bhasha Chuniye (Select Language)
            </label>
            <select
              id="language-select"
              value={selectedLanguage}
              onChange={(e) => onLanguageChange(e.target.value)}
              className="text-xs bg-stone-50 hover:bg-stone-100/90 border border-dukaan-border text-dukaan-text font-semibold rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-dukaan-primary cursor-pointer transition-colors shadow-xs"
            >
              <option value="hi-IN">हिंदी</option>
              <option value="hi-en">Hinglish</option>
              <option value="en-IN">English</option>
            </select>
          </div>

          <div className="h-5 w-px bg-dukaan-border/80 hidden xs:block" aria-hidden="true" />

          {/* Voice Chat button */}
          <button
            onClick={() => onTabChange("voice")}
            className={`px-3 py-1.5 rounded-lg border transition-all active:scale-95 flex items-center gap-1.5 text-xs font-semibold ${
              activeTab === "voice"
                ? "bg-dukaan-primary text-white border-dukaan-primary shadow-xs"
                : "bg-white text-dukaan-text border-dukaan-border hover:bg-stone-50 shadow-2xs"
            }`}
            aria-label="Voice Chat"
            title="Awaaz Chat (Transcript)"
          >
            <Mic className="w-3.5 h-3.5" aria-hidden="true" />
            <span>Voice</span>
          </button>

          {/* Order History button */}
          <button
            onClick={() => onTabChange("history")}
            className={`px-2.5 py-1.5 rounded-lg border transition-all active:scale-95 flex items-center gap-1.5 text-xs font-semibold ${
              activeTab === "history"
                ? "bg-dukaan-primary text-white border-dukaan-primary shadow-xs"
                : "bg-white text-dukaan-text border-dukaan-border hover:bg-stone-50 shadow-2xs"
            }`}
            aria-label="Order History"
            title="Pichle Orders"
          >
            <History className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="hidden md:inline">History</span>
          </button>

          {/* Cart button */}
          <button
            onClick={() => onTabChange("cart")}
            className={`relative px-3 py-1.5 rounded-lg border transition-all active:scale-95 flex items-center gap-1.5 text-xs font-semibold ${
              activeTab === "cart"
                ? "bg-dukaan-primary text-white border-dukaan-primary shadow-xs"
                : "bg-white text-dukaan-text border-dukaan-border hover:bg-stone-50 shadow-2xs"
            }`}
            aria-label={`Cart with ${cartCount} items`}
          >
            <ShoppingBag className="w-3.5 h-3.5" aria-hidden="true" />
            <span className="hidden sm:inline">Cart</span>
            {cartCount > 0 && (
              <span className="bg-dukaan-primary text-white text-[10px] font-bold px-1.5 py-0.2 rounded-full min-w-4 text-center">
                {cartCount}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
