"use client";

import React from "react";

/**
 * ShopAmbientBackground
 * A classy, minimal, animated Kirana store ambient backdrop.
 * Features:
 * - Minimalist shop awning (chhatri / canopy) with subtle ambient warmth
 * - Delicate, floating line-art kirana motifs (tarazu / balance scales, tea leaves, spice jars, grains)
 * - Pure compositor-only CSS animations (transform, opacity) with 60fps performance
 * - Strictly respects prefers-reduced-motion
 * - Non-intrusive low opacity (0.04 - 0.12) ensuring 100% contrast and legibility
 */
export function ShopAmbientBackground() {
  return (
    <div
      className="fixed inset-0 pointer-events-none select-none overflow-hidden -z-10 bg-[#FAF8F5]"
      aria-hidden="true"
    >
      {/* Warm Ambient Radial Underglows */}
      <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[600px] h-[340px] rounded-full bg-gradient-to-b from-orange-200/25 via-amber-100/20 to-transparent blur-3xl" />
      <div className="absolute top-1/3 -left-32 w-80 h-80 rounded-full bg-amber-100/15 blur-3xl animate-pulse-subtle" />
      <div className="absolute bottom-20 -right-28 w-96 h-96 rounded-full bg-orange-100/20 blur-3xl animate-pulse-subtle" />

      {/* Top Shop Awning (Canopy Silhouette) */}
      <div className="absolute top-0 left-0 right-0 h-14 opacity-40">
        <svg
          className="w-full h-full object-cover"
          viewBox="0 0 1200 60"
          preserveAspectRatio="none"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Alternating Awning Stripes with subtle warm terracotta & cream */}
          <defs>
            <pattern id="awning-stripes" width="60" height="40" patternUnits="userSpaceOnUse">
              <rect x="0" y="0" width="30" height="40" fill="#C2410C" fillOpacity="0.08" />
              <rect x="30" y="0" width="30" height="40" fill="#D97706" fillOpacity="0.04" />
            </pattern>
            <linearGradient id="awning-fade" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#FAF8F5" stopOpacity="0" />
              <stop offset="90%" stopColor="#FAF8F5" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#FAF8F5" stopOpacity="1" />
            </linearGradient>
          </defs>
          <rect x="0" y="0" width="1200" height="40" fill="url(#awning-stripes)" />
          {/* Subtle Scalloped Awning Fringe */}
          <path
            d="M0,40 Q15,48 30,40 Q45,48 60,40 Q75,48 90,40 Q105,48 120,40 Q135,48 150,40 Q165,48 180,40 Q195,48 210,40 Q225,48 240,40 Q255,48 270,40 Q285,48 300,40 Q315,48 330,40 Q345,48 360,40 Q375,48 390,40 Q405,48 420,40 Q435,48 450,40 Q465,48 480,40 Q495,48 510,40 Q525,48 540,40 Q555,48 570,40 Q585,48 600,40 Q615,48 630,40 Q645,48 660,40 Q675,48 690,40 Q705,48 720,40 Q735,48 750,40 Q765,48 780,40 Q795,48 810,40 Q825,48 840,40 Q855,48 870,40 Q885,48 900,40 Q915,48 930,40 Q945,48 960,40 Q975,48 990,40 Q1005,48 1020,40 Q1035,48 1050,40 Q1065,48 1080,40 Q1095,48 1110,40 Q1125,48 1140,40 Q1155,48 1170,40 Q1185,48 1200,40 L1200,60 L0,60 Z"
            fill="#FAF8F5"
          />
          <line x1="0" y1="40" x2="1200" y2="40" stroke="#C2410C" strokeOpacity="0.12" strokeWidth="1" />
        </svg>
      </div>

      {/* Floating Classy Kirana Motif 1: Classic Weighing Scale (Tarazu) - Left Top */}
      <div className="absolute top-28 left-6 sm:left-14 opacity-[0.07] text-stone-800 animate-float-slow">
        <svg width="110" height="110" viewBox="0 0 100 100" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
          {/* Scale Stand */}
          <line x1="50" y1="12" x2="50" y2="85" />
          <path d="M35 85 L65 85" />
          <circle cx="50" cy="12" r="3.5" fill="currentColor" fillOpacity="0.2" />
          {/* Balance Beam */}
          <line x1="20" y1="26" x2="80" y2="26" />
          {/* Left Pan */}
          <line x1="20" y1="26" x2="10" y2="52" />
          <line x1="20" y1="26" x2="30" y2="52" />
          <path d="M8 52 Q20 62 32 52 Z" fill="currentColor" fillOpacity="0.1" />
          {/* Right Pan */}
          <line x1="80" y1="26" x2="70" y2="52" />
          <line x1="80" y1="26" x2="90" y2="52" />
          <path d="M68 52 Q80 62 92 52 Z" fill="currentColor" fillOpacity="0.1" />
        </svg>
      </div>

      {/* Floating Classy Kirana Motif 2: Spice / Grocery Mart Glass Jar - Right Upper */}
      <div className="absolute top-36 right-6 sm:right-16 opacity-[0.06] text-stone-800 animate-float-reverse">
        <svg width="95" height="115" viewBox="0 0 80 100" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          {/* Jar Lid */}
          <rect x="25" y="10" width="30" height="7" rx="2" fill="currentColor" fillOpacity="0.15" />
          <line x1="28" y1="17" x2="52" y2="17" />
          {/* Jar Body */}
          <path d="M22 22 L58 22 C64 22 68 26 68 32 L68 82 C68 88 64 92 58 92 L22 92 C16 92 12 88 12 82 L12 32 C12 26 16 22 22 22 Z" />
          {/* Subtle Label */}
          <rect x="22" y="44" width="36" height="22" rx="3" strokeDasharray="2 2" fill="currentColor" fillOpacity="0.05" />
          <line x1="28" y1="52" x2="52" y2="52" />
          <line x1="32" y1="58" x2="48" y2="58" />
        </svg>
      </div>

      {/* Floating Classy Kirana Motif 3: Tea Leaves / Elaichi Botanical Accent - Left Middle */}
      <div className="absolute top-1/2 left-8 sm:left-20 opacity-[0.07] text-amber-900 animate-float-reverse">
        <svg width="80" height="80" viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          {/* Stem & Leaves */}
          <path d="M12 52 C22 42 36 26 48 12" />
          <path d="M30 34 C30 22 42 20 44 20 C44 32 34 34 30 34 Z" fill="currentColor" fillOpacity="0.1" />
          <path d="M22 42 C14 36 16 24 26 24 C26 34 24 40 22 42 Z" fill="currentColor" fillOpacity="0.1" />
          <path d="M40 24 C40 14 52 12 54 12 C54 22 46 24 40 24 Z" fill="currentColor" fillOpacity="0.1" />
        </svg>
      </div>

      {/* Floating Classy Kirana Motif 4: Classic Indian Milk Bottle / Dairy Pouch - Right Middle */}
      <div className="absolute top-[58%] right-8 sm:right-24 opacity-[0.06] text-stone-800 animate-float-slow">
        <svg width="75" height="100" viewBox="0 0 60 90" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          {/* Bottle Cap & Neck */}
          <rect x="22" y="8" width="16" height="6" rx="1.5" />
          <path d="M24 14 L24 24 L14 36 L14 80 C14 84 17 86 21 86 L39 86 C43 86 46 84 46 80 L46 36 L36 24 L36 14 Z" />
          {/* Milk Level wave */}
          <path d="M16 54 Q30 50 44 54" strokeDasharray="3 2" />
          <line x1="22" y1="64" x2="38" y2="64" />
        </svg>
      </div>

      {/* Floating Classy Kirana Motif 5: Jute Sack / Grain Bag (Bora) - Left Lower */}
      <div className="absolute bottom-24 left-10 sm:left-24 opacity-[0.06] text-amber-900 animate-float-slow">
        <svg width="90" height="95" viewBox="0 0 80 85" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          {/* Sack gathered top */}
          <path d="M30 18 Q40 22 50 18 Q45 10 40 10 Q35 10 30 18 Z" fill="currentColor" fillOpacity="0.15" />
          <line x1="33" y1="20" x2="47" y2="20" strokeWidth="2.5" />
          {/* Sack body */}
          <path d="M30 20 C18 28 14 42 16 70 C16 76 22 80 40 80 C58 80 64 76 64 70 C66 42 62 28 50 20 Z" />
          {/* Weave texture lines */}
          <line x1="28" y1="42" x2="52" y2="42" strokeDasharray="2 3" />
          <line x1="26" y1="54" x2="54" y2="54" strokeDasharray="2 3" />
          <line x1="30" y1="66" x2="50" y2="66" strokeDasharray="2 3" />
        </svg>
      </div>

      {/* Floating Classy Kirana Motif 6: Tea Cup Silhouette (Cutting Chai) - Right Lower */}
      <div className="absolute bottom-28 right-10 sm:right-28 opacity-[0.06] text-stone-800 animate-float-reverse">
        <svg width="85" height="75" viewBox="0 0 70 60" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          {/* Saucer */}
          <path d="M10 50 Q35 56 60 50" strokeWidth="2" />
          {/* Cup */}
          <path d="M18 16 L22 46 Q35 50 48 46 L52 16 Z" />
          {/* Handle */}
          <path d="M51 22 C59 22 61 36 49 38" />
          {/* Steam ripples */}
          <path d="M28 8 Q31 4 33 8" strokeDasharray="1 1" />
          <path d="M37 7 Q40 3 42 7" strokeDasharray="1 1" />
        </svg>
      </div>

      {/* Gentle Floating Golden Spice Grain Dots */}
      <div className="absolute top-[22%] left-[45%] w-1.5 h-1.5 rounded-full bg-amber-600/20 animate-drift-up-1" />
      <div className="absolute top-[48%] right-[38%] w-2 h-2 rounded-full bg-orange-600/15 animate-drift-up-2" />
      <div className="absolute top-[72%] left-[32%] w-1.5 h-1.5 rounded-full bg-amber-700/20 animate-drift-up-1" />
      <div className="absolute top-[85%] right-[44%] w-2 h-2 rounded-full bg-orange-700/15 animate-drift-up-2" />
    </div>
  );
}

