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
  hasSpoken?: boolean;
  isCallMode?: boolean;
  onToggleCallMode?: () => void;
  callModeToast?: string | null;
  onDismissToast?: () => void;
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
  hasSpoken = false,
  isCallMode = true,
  onToggleCallMode,
  callModeToast,
  onDismissToast,
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
      {/* Call Mode Status Bar */}
      <div className="shrink-0">
        {isCallMode ? (
          <div className="flex items-center justify-between px-4 py-2 bg-emerald-50 border-b border-emerald-200/80 text-xs text-emerald-900 shadow-xs">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-600"></span>
              </span>
              <span className="font-semibold">Kirana Call Chalu Hai</span>
              <span className="text-[10px] text-emerald-700 bg-emerald-100/90 px-1.5 py-0.5 rounded font-medium">Hands-free Auto-VAD</span>
            </div>
            {onToggleCallMode && (
              <button
                type="button"
                onClick={onToggleCallMode}
                className="text-[11px] font-bold text-emerald-800 hover:text-emerald-950 px-2 py-0.5 rounded border border-emerald-300 bg-white shadow-xs transition-colors"
              >
                Call Pause
              </button>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-between px-4 py-2 bg-stone-100 border-b border-stone-200 text-xs text-stone-700">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-stone-400"></span>
              <span className="font-medium">Push-to-Talk Mode</span>
            </div>
            {onToggleCallMode && (
              <button
                type="button"
                onClick={onToggleCallMode}
                className="text-[11px] font-bold text-dukaan-primary hover:text-dukaan-primaryDark px-2 py-0.5 rounded border border-dukaan-primary/30 bg-white shadow-xs transition-colors"
              >
                📞 Call Chalu Karein
              </button>
            )}
          </div>
        )}
      </div>

      {/* Call Mode Toast Notice */}
      {callModeToast && (
        <div className="mx-4 mt-2 p-2.5 bg-amber-50 border border-amber-200 rounded-xl flex items-center justify-between text-xs text-amber-900 shadow-sm animate-in fade-in">
          <span>{callModeToast}</span>
          <div className="flex items-center gap-2">
            {onToggleCallMode && (
              <button
                type="button"
                onClick={onToggleCallMode}
                className="font-bold underline text-amber-900 hover:text-amber-950"
              >
                Resume
              </button>
            )}
            {onDismissToast && (
              <button
                type="button"
                onClick={onDismissToast}
                className="text-amber-700 hover:text-amber-900 p-0.5"
                aria-label="Dismiss toast"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      )}

      {/* Transcript Log Area */}
      <div className="flex-1 overflow-y-auto pb-4 pt-2">
        <TranscriptList
          messages={messages}
          onPlayAudio={onPlayAudio}
          isPlayingAudio={isPlayingAudio}
          activeAudioUrl={activeAudioUrl}
          onSelectClarification={onSelectClarification}
        />
      </div>

      {/* Barge-In / Assistant Speaking indicator */}
      {isPlayingAudio && !isRecording && (
        <div className="mx-4 mb-2 p-2.5 bg-orange-50 border border-orange-200 rounded-xl flex items-center justify-between text-xs text-orange-950 shadow-sm animate-in fade-in">
          <span className="flex items-center gap-2 font-medium">
            <Volume2 className="w-4 h-4 text-dukaan-primary animate-pulse shrink-0" aria-hidden="true" />
            <span>Dukaandaar bol raha hai...</span>
          </span>
          <button
            type="button"
            onClick={onStartRecording}
            className="px-2.5 py-1 bg-dukaan-primary hover:bg-dukaan-primaryDark text-white font-bold rounded-lg text-xs shadow-xs transition-all active:scale-95"
          >
            Barge-in (Boliye)
          </button>
        </div>
      )}

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
              <span>
                {hasSpoken
                  ? `Sun rahe hain... (${formatTime(duration)})`
                  : `Boliye, sun rahe hain... (${formatTime(duration)})`}
              </span>
            </div>

            {/* Live visual waveform */}
            <Waveform isRecording={isRecording} audioLevel={audioLevel} />

            {isCallMode && (
              <div className="text-[10px] text-dukaan-muted text-center">
                {hasSpoken
                  ? "Aapke chup hote hi order apne aap bheja jayega"
                  : "Boliye, bolte hi mic capture karega"}
              </div>
            )}

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
