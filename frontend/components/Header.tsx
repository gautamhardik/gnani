"use client";

import React from "react";
import { Store } from "@/types/api";
import { Store as StoreIcon, ShoppingBag, Clock } from "lucide-react";

interface HeaderProps {
  store: Store | null;
  selectedLanguage: string;
  onLanguageChange: (lang: string) => void;
  cartCount: number;
  activeTab: "home" | "voice" | "cart";
  onTabChange: (tab: "home" | "voice" | "cart") => void;
}

export function Header({
  store,
  selectedLanguage,
  onLanguageChange,
  cartCount,
  activeTab,
  onTabChange,
}: HeaderProps) {
  const storeName = store?.store_name || "Sharma General Store";
  const isOpen = store?.is_open ?? true;

  return (
    <header className="sticky top-0 z-40 bg-dukaan-card border-b border-dukaan-border shadow-warm">
      <div className="max-w-md mx-auto px-4 py-3 flex items-center justify-between">
        {/* Store Brand & Identity */}
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-xl bg-dukaan-primary/10 border border-dukaan-primary/20 flex items-center justify-center text-dukaan-primary font-bold shadow-sm">
            <StoreIcon className="w-5 h-5 text-dukaan-primary" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-base font-bold text-dukaan-text leading-tight tracking-tight">
              {storeName}
            </h1>
            <div className="flex items-center gap-2 mt-0.5 text-xs text-dukaan-muted">
              <span
                className={`inline-flex items-center gap-1 font-medium ${
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
              <span>•</span>
              <span className="flex items-center gap-0.5">
                <Clock className="w-3 h-3" aria-hidden="true" />
                {store?.opening_time || "8 AM"} - {store?.closing_time || "10 PM"}
              </span>
            </div>
          </div>
        </div>

        {/* Language selector & Cart pill */}
        <div className="flex items-center gap-2">
          {/* Language preference dropdown */}
          <div className="relative">
            <label htmlFor="language-select" className="sr-only">
              Bhasha Chuniye (Select Language)
            </label>
            <select
              id="language-select"
              value={selectedLanguage}
              onChange={(e) => onLanguageChange(e.target.value)}
              className="text-xs bg-dukaan-canvas border border-dukaan-border text-dukaan-text font-medium rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-dukaan-primary cursor-pointer"
            >
              <option value="hi-IN">हिंदी (Hindi)</option>
              <option value="hi-en">Hinglish</option>
              <option value="en-IN">English</option>
            </select>
          </div>

          {/* Cart button */}
          <button
            onClick={() => onTabChange("cart")}
            className={`relative p-2 rounded-lg border transition-colors ${
              activeTab === "cart"
                ? "bg-dukaan-primary text-white border-dukaan-primary"
                : "bg-dukaan-canvas text-dukaan-text border-dukaan-border hover:bg-stone-100"
            }`}
            aria-label={`Cart with ${cartCount} items`}
          >
            <ShoppingBag className="w-5 h-5" aria-hidden="true" />
            {cartCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-dukaan-primary text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center border-2 border-white">
                {cartCount}
              </span>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
