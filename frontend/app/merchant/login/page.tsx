"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { Store, Lock, User, AlertCircle, ArrowLeft, Loader2 } from "lucide-react";
import { loginMerchant } from "@/lib/merchantApi";

export default function MerchantLoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setErrorMessage("Kripya username aur password dono bharein.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      await loginMerchant({ username: username.trim(), password: password.trim() });
      router.push("/merchant");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message || "Login vifal raha. Kripya punah prayas karein.");
      } else {
        setErrorMessage("Galat credentials ya network samasya.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-dukaan-canvas flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Back Link */}
        <div className="mb-6">
          <button
            onClick={() => router.push("/")}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-dukaan-muted hover:text-dukaan-text transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Grahak Dukan par vapas jayein (Customer View)
          </button>
        </div>

        {/* Card */}
        <div className="bg-dukaan-card border border-dukaan-border rounded-2xl p-6 sm:p-8 shadow-warm">
          {/* Header */}
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-dukaan-primary/10 text-dukaan-primary mb-3">
              <Store className="w-7 h-7" />
            </div>
            <h1 className="text-2xl font-bold text-dukaan-text tracking-tight">
              DukaanSaathi Merchant
            </h1>
            <p className="text-xs text-dukaan-muted mt-1 font-medium">
              Sharma General Store &mdash; Dukandar Portal
            </p>
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <div
              role="alert"
              className="mb-5 p-3 rounded-xl bg-dukaan-errorBg border border-dukaan-error/20 flex items-start gap-2.5 text-xs text-dukaan-error"
            >
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="username"
                className="block text-xs font-semibold text-dukaan-text mb-1.5"
              >
                Dukandar Username (यूजरनेम)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-dukaan-muted">
                  <User className="w-4 h-4" />
                </div>
                <input
                  id="username"
                  name="username"
                  type="text"
                  required
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. sharma"
                  className="w-full pl-9 pr-3.5 py-2.5 bg-dukaan-canvas border border-dukaan-border rounded-xl text-sm text-dukaan-text focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30 focus:border-dukaan-primary transition-all"
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-xs font-semibold text-dukaan-text mb-1.5"
              >
                Password (पासवर्ड)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-dukaan-muted">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-3.5 py-2.5 bg-dukaan-canvas border border-dukaan-border rounded-xl text-sm text-dukaan-text focus:outline-none focus:ring-2 focus:ring-dukaan-primary/30 focus:border-dukaan-primary transition-all"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 py-3 px-4 bg-dukaan-primary hover:bg-dukaan-primaryDark text-white font-semibold text-sm rounded-xl shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-dukaan-primary/40 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Satyaapan kiya ja raha hai...</span>
                  </>
                ) : (
                  <span>Login Karein (लॉग इन)</span>
                )}
              </button>
            </div>
          </form>

          {/* Security Notice */}
          <div className="mt-6 pt-5 border-t border-dukaan-border/60 text-center">
            <p className="text-[11px] text-dukaan-muted">
              Surakshit Backend Auth • Demo Kirana Credentials: <br />
              <code className="px-1.5 py-0.5 bg-dukaan-canvas rounded border border-dukaan-border text-[10px] font-mono text-dukaan-text">
                sharma
              </code>{" "}
              /{" "}
              <code className="px-1.5 py-0.5 bg-dukaan-canvas rounded border border-dukaan-border text-[10px] font-mono text-dukaan-text">
                kirana@2026
              </code>
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}
