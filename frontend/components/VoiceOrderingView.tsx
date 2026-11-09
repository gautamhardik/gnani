"use client";

import React from "react";
import { Mic, Square, X, Loader2, AlertCircle, ShoppingBag, Volume2 } from "lucide-react";
import { Waveform } from "@/components/Waveform";
import { TranscriptList, ConversationMessage } from "@/components/TranscriptList";
import { CartItem } from "@/types/api";

interface VoiceOrderingViewProps {
  messages: ConversationMessage[];
  isRecording: boolean;
  isProcessing: boolean;
  duration: number;
  audioLevel: number;
  errorMessage: string | null;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onCancelRecording: () => void;
  onPlayAudio: (url: string) => void;
  isPlayingAudio: boolean;
  activeAudioUrl: string | null;
  autoplayBlocked: boolean;
  onSelectClarification?: (option: string) => void;
  cartItems: CartItem[];
  cartTotal: number;
  onViewCart: () => void;
}

export function VoiceOrderingView({
  messages,
  isRecording,
  isProcessing,
  duration,
  audioLevel,
  errorMessage,
  onStartRecording,
  onStopRecording,
  onCancelRecording,
  onPlayAudio,
  isPlayingAudio,
  activeAudioUrl,
  autoplayBlocked,
  onSelectClarification,
  cartItems,
  cartTotal,
  onViewCart,
}: VoiceOrderingViewProps) {
  // Format recording duration mm:ss
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex flex-col h-[calc(100vh-65px)] max-w-md mx-auto">
      {/* Transcript Log Area */}
      <div className="flex-1 overflow-y-auto pb-4">
        <TranscriptList
          messages={messages}
          onPlayAudio={onPlayAudio}
          isPlayingAudio={isPlayingAudio}
          activeAudioUrl={activeAudioUrl}
          onSelectClarification={onSelectClarification}
        />
      </div>

      {/* Autoplay blocked banner */}
      {autoplayBlocked && activeAudioUrl && (
        <div className="mx-4 mb-2 p-2.5 bg-amber-50 border border-amber-200 rounded-xl flex items-center justify-between text-xs text-amber-900 shadow-sm animate-in fade-in">
          <span className="flex items-center gap-1.5 font-medium">
            <Volume2 className="w-4 h-4 text-amber-700" aria-hidden="true" />
            Assistant ka jawab sunein
          </span>
          <button
            onClick={() => onPlayAudio(activeAudioUrl)}
            className="px-3 py-1 bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded-lg text-xs transition-colors"
          >
            Play Karein
          </button>
        </div>
      )}

      {/* Error / Permission Banner */}
      {errorMessage && (
        <div className="mx-4 mb-3 p-3 bg-red-50 border border-red-200 rounded-xl flex items-start gap-2 text-xs text-red-700 shadow-sm">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
          <div className="leading-relaxed">{errorMessage}</div>
        </div>
      )}

      {/* Cart bottom preview strip */}
      {cartItems.length > 0 && !isRecording && (
        <div className="mx-4 mb-2 p-2.5 bg-dukaan-card border border-dukaan-border rounded-xl flex items-center justify-between shadow-warm">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-orange-100 text-dukaan-primary flex items-center justify-center">
              <ShoppingBag className="w-4 h-4" aria-hidden="true" />
            </div>
            <div>
              <div className="text-xs font-bold text-dukaan-text">
                {cartItems.length} {cartItems.length === 1 ? "Item" : "Items"} • ₹{Number(cartTotal || 0).toFixed(2)}
              </div>
              <div className="text-[10px] text-dukaan-muted">Verified Server Rates</div>
            </div>
          </div>
          <button
            onClick={onViewCart}
            className="text-xs font-bold text-dukaan-primary hover:text-dukaan-primaryDark px-2.5 py-1 rounded-lg bg-orange-50 border border-orange-200/60"
          >
            Cart Kholein &rarr;
          </button>
        </div>
      )}

      {/* Voice Controls Dock */}
      <div className="bg-dukaan-card border-t border-dukaan-border p-4 shadow-floating">
        {isRecording ? (
          <div className="flex flex-col items-center gap-2 animate-in fade-in duration-150">
            {/* Live timer & indicator */}
            <div className="flex items-center gap-2 text-xs font-semibold text-dukaan-primary">
              <span className="w-2.5 h-2.5 rounded-full bg-red-600 animate-ping" aria-hidden="true" />
              <span>Record ho raha hai: {formatTime(duration)}</span>
            </div>

            {/* Live visual waveform */}
            <Waveform isRecording={isRecording} audioLevel={audioLevel} />

            {/* Control buttons */}
            <div className="flex items-center gap-4 w-full justify-center mt-1">
              <button
                type="button"
                onClick={onCancelRecording}
                className="p-3 text-stone-500 hover:text-dukaan-error hover:bg-stone-100 rounded-full border border-dukaan-border transition-colors"
                aria-label="Cancel recording"
              >
                <X className="w-5 h-5" aria-hidden="true" />
              </button>

              <button
                type="button"
                onClick={onStopRecording}
                className="py-3 px-6 rounded-full bg-red-600 hover:bg-red-700 text-white font-bold text-sm shadow-warm flex items-center gap-2 transition-all transform active:scale-95"
              >
                <Square className="w-4 h-4 fill-white" aria-hidden="true" />
                <span>Rukiye aur Bhejiye</span>
              </button>
            </div>
          </div>
        ) : isProcessing ? (
          <div className="py-4 flex flex-col items-center justify-center gap-2">
            <Loader2 className="w-8 h-8 text-dukaan-primary animate-spin" aria-hidden="true" />
            <div className="text-xs font-bold text-dukaan-text">Prisma sun raha hai...</div>
            <div className="text-[11px] text-dukaan-muted">Order Engine se check ho raha hai</div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <button
              type="button"
              onClick={onStartRecording}
              className="w-16 h-16 rounded-full bg-dukaan-primary hover:bg-dukaan-primaryDark text-white flex items-center justify-center shadow-warm transition-all transform active:scale-95 focus:ring-4 focus:ring-orange-200"
              aria-label="Start voice recording"
            >
              <Mic className="w-8 h-8" aria-hidden="true" />
            </button>
            <div className="text-xs font-semibold text-dukaan-text">Mic dabayein aur boliye</div>
            <div className="text-[11px] text-dukaan-muted">Hindi ya Hinglish mein grocery mangwayein</div>
          </div>
        )}
      </div>
    </div>
  );
}
