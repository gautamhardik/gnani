"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { Store, RefreshCw, LogOut, ExternalLink, ShieldCheck } from "lucide-react";
import { clearStoredToken } from "@/lib/merchantApi";

interface MerchantHeaderProps {
  storeName: string;
  onRefresh: () => void;
  isRefreshing: boolean;
}

export function MerchantHeader({
  storeName,
  onRefresh,
  isRefreshing,
}: MerchantHeaderProps) {
  const router = useRouter();

  const handleLogout = () => {
    clearStoredToken();
    router.push("/merchant/login");
  };

  return (
    <header className="bg-dukaan-card border-b border-dukaan-border sticky top-0 z-30 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex items-center justify-between">
        {/* Brand & Store */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-dukaan-primary flex items-center justify-center text-white shadow-warm">
            <Store className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-bold text-dukaan-text leading-tight">
                {storeName || "Sharma General Store"}
              </h1>
              <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-dukaan-successBg text-dukaan-success border border-dukaan-success/20">
                <span className="w-1.5 h-1.5 rounded-full bg-dukaan-success animate-pulse" />
                Live Store
              </span>
            </div>
            <p className="text-xs text-dukaan-muted flex items-center gap-1 mt-0.5">
              <ShieldCheck className="w-3.5 h-3.5 text-dukaan-accent" />
              Dukandar Operations Portal (दुकानदार डैशबोर्ड)
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            aria-label="Refresh operational metrics"
            className="flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-xl border border-dukaan-border hover:bg-dukaan-canvas text-dukaan-text transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">Taaza Karein (Refresh)</span>
          </button>

          <button
            onClick={() => window.open("/", "_blank")}
            aria-label="Open customer store view"
            className="hidden md:flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-xl border border-dukaan-border hover:bg-dukaan-canvas text-dukaan-muted hover:text-dukaan-text transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            <span>Grahak View</span>
          </button>

          <button
            onClick={handleLogout}
            aria-label="Log out from merchant portal"
            className="flex items-center gap-1.5 text-xs font-semibold px-3 py-2 rounded-xl bg-dukaan-canvas hover:bg-dukaan-errorBg text-dukaan-muted hover:text-dukaan-error border border-dukaan-border transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}

