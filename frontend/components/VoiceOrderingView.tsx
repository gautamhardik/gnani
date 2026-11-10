"use client";

import React from "react";
import { Mic, Square, X, Loader2, AlertCircle, ShoppingBag, Volume2, Phone, PhoneOff, PhoneCall, CheckCircle } from "lucide-react";
import { Waveform } from "@/components/Waveform";
import { TranscriptList, ConversationMessage } from "@/components/TranscriptList";
import { CartItem, Order } from "@/types/api";

interface VoiceOrderingViewProps {
  messages: ConversationMessage[];
  isRecording: boolean;
  isProcessing: boolean;
  duration: number;
  audioLevel: number;
  hasSpoken?: boolean;
  isCallMode?: boolean;
  isCallActive?: boolean;
  onStartCall?: () => void;
  onEndCall?: () => void;
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
  confirmedOrder?: Order | null;
  onViewOrderReceipt?: () => void;
  selectedLanguage?: string;
}

export function VoiceOrderingView({
  messages,
  isRecording,
  isProcessing,
  duration,
  audioLevel,
  hasSpoken = false,
  isCallMode = true,
  isCallActive = false,
  onStartCall,
  onEndCall,
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
  confirmedOrder,
  onViewOrderReceipt,
  selectedLanguage = "hi-IN",
}: VoiceOrderingViewProps) {
  // Format recording duration mm:ss
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex flex-col h-[calc(100vh-65px)] max-w-md mx-auto">
      {/* Placed Order Notification Banner */}
      {confirmedOrder && (
        <div className="mx-4 mt-2 p-3 bg-emerald-50 border border-emerald-300 rounded-xl flex items-center justify-between shadow-xs animate-in fade-in duration-200 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
              <CheckCircle className="w-5 h-5 text-emerald-600" />
            </div>
            <div>
              <div className="text-xs font-bold text-emerald-950">
                Order #{confirmedOrder.order_id.slice(-6).toUpperCase()} Bhej Diya Gaya!
              </div>
              <div className="text-[11px] text-emerald-700 font-medium">
                Kul: ₹{Number(confirmedOrder.total_amount || 0).toFixed(2)} • Shopkeeper review pending
              </div>
            </div>
          </div>
          {onViewOrderReceipt && (
            <button
              type="button"
              onClick={onViewOrderReceipt}
              className="text-xs font-bold text-emerald-800 bg-white border border-emerald-300 hover:bg-emerald-100 px-3 py-1.5 rounded-lg transition-colors shadow-xs shrink-0"
            >
              Receipt
            </button>
          )}
        </div>
      )}

      {/* Call Mode Status Bar */}
      <div className="shrink-0">
        {isCallActive ? (
          <div className="flex items-center justify-between px-4 py-2.5 bg-emerald-600 text-white text-xs shadow-md">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-200"></span>
              </span>
              <span className="font-bold tracking-wide">Sharma Ji Call Chalu Hai</span>
              <span className="text-[10px] bg-emerald-700/80 text-emerald-100 px-2 py-0.5 rounded-full font-medium">Hands-Free</span>
            </div>
            {onEndCall && (
              <button
                type="button"
                onClick={onEndCall}
                className="flex items-center gap-1.5 text-xs font-bold text-white bg-red-600 hover:bg-red-700 active:scale-95 px-3 py-1 rounded-full shadow-xs transition-all"
              >
                <PhoneOff className="w-3.5 h-3.5" />
                <span>Call End</span>
              </button>
            )}
          </div>
        ) : isCallMode ? (
          <div className="flex items-center justify-between px-4 py-2 bg-emerald-50 border-b border-emerald-200/80 text-xs text-emerald-900 shadow-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-600"></span>
              <span className="font-semibold">Hands-Free Voice Mode</span>
            </div>
            {onStartCall ? (
              <button
                type="button"
                onClick={onStartCall}
                className="flex items-center gap-1.5 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 active:scale-95 px-3 py-1 rounded-full shadow-xs transition-all"
              >
                <Phone className="w-3.5 h-3.5" />
                <span>Call Shuru Karein</span>
              </button>
            ) : onToggleCallMode && (
              <button
                type="button"
                onClick={onToggleCallMode}
                className="text-[11px] font-bold text-emerald-800 hover:text-emerald-950 px-2 py-0.5 rounded border border-emerald-300 bg-white shadow-xs transition-colors"
              >
                Push-to-Talk
              </button>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-between px-4 py-2 bg-stone-100 border-b border-stone-200 text-xs text-stone-700">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-stone-400"></span>
              <span className="font-medium">Push-to-Talk Mode</span>
            </div>
            {onStartCall ? (
              <button
                type="button"
                onClick={onStartCall}
                className="text-xs font-bold text-dukaan-primary hover:text-dukaan-primaryDark px-3 py-1 rounded-full border border-dukaan-primary/30 bg-white shadow-xs transition-colors flex items-center gap-1"
              >
                <Phone className="w-3.5 h-3.5" />
                <span>Call Shuru Karein</span>
              </button>
            ) : onToggleCallMode && (
              <button
                type="button"
                onClick={onToggleCallMode}
                className="text-[11px] font-bold text-dukaan-primary hover:text-dukaan-primaryDark px-2 py-0.5 rounded border border-dukaan-primary/30 bg-white shadow-xs transition-colors"
              >
                Hands-Free Mode
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

      {/* Empty State / Welcome to Call Hero if not started yet */}
      {!isCallActive && messages.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
          <div className="w-20 h-20 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center shadow-md mb-4 animate-pulse">
            <PhoneCall className="w-10 h-10" />
          </div>
          <h2 className="text-xl font-bold text-dukaan-text mb-2">Sharma Ji Voice Assistant</h2>
          <p className="text-sm text-dukaan-muted mb-6 max-w-xs leading-relaxed">
            Ek baar call shuru karein. Sharma Ji aapse baat karenge aur poori baatcheet bina baar-baar click kiye lagatar chalegi.
          </p>
          {onStartCall ? (
            <button
              type="button"
              onClick={onStartCall}
              className="py-3.5 px-8 bg-emerald-600 hover:bg-emerald-700 active:scale-95 text-white font-bold text-base rounded-full shadow-lg flex items-center gap-2.5 transition-all"
            >
              <Phone className="w-5 h-5 fill-white" />
              <span>Kirana Call Shuru Karein</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={onStartRecording}
              className="py-3.5 px-8 bg-dukaan-primary hover:bg-dukaan-primaryDark active:scale-95 text-white font-bold text-base rounded-full shadow-lg flex items-center gap-2.5 transition-all"
            >
              <Mic className="w-5 h-5 fill-white" />
              <span>Mic On Karein Aur Boliye</span>
            </button>
          )}
        </div>
      ) : (
        /* Transcript Log Area */
        <div className="flex-1 overflow-y-auto pb-4 pt-2">
          <TranscriptList
            messages={messages}
            onPlayAudio={onPlayAudio}
            isPlayingAudio={isPlayingAudio}
            activeAudioUrl={activeAudioUrl}
            onSelectClarification={onSelectClarification}
            selectedLanguage={selectedLanguage}
          />
        </div>
      )}

      {/* Barge-In / Assistant Speaking indicator */}
      {isPlayingAudio && !isRecording && (
        <div className="mx-4 mb-2 p-2.5 bg-blue-50 border border-blue-200 rounded-xl flex items-center justify-between text-xs text-blue-950 shadow-sm animate-in fade-in">
          <span className="flex items-center gap-2 font-medium">
            <Volume2 className="w-4 h-4 text-blue-600 animate-pulse shrink-0" aria-hidden="true" />
            <span>Sharma Ji bol rahe hain...</span>
          </span>
          <button
            type="button"
            onClick={onStartRecording}
            className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg text-xs shadow-xs transition-all active:scale-95"
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
            Sharma Ji ka jawab sunein
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
              <div className="text-[10px] text-dukaan-muted">Verified Store Prices</div>
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
            <div className="flex items-center gap-2 text-xs font-semibold text-emerald-700">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 animate-ping" aria-hidden="true" />
              <span>
                {hasSpoken
                  ? `Sun rahe hain... (${formatTime(duration)})`
                  : `Boliye, sun rahe hain... (${formatTime(duration)})`}
              </span>
            </div>

            {/* Live visual waveform */}
            <Waveform isRecording={isRecording} audioLevel={audioLevel} />

            <div className="text-[11px] text-dukaan-muted text-center font-medium">
              {hasSpoken
                ? "Aapke bolna band karte hi Sharma Ji jawab denge (Hands-Free)"
                : "Boliye, mic aapki aawaaz sun raha hai"}
            </div>

            {/* Optional manual control buttons */}
            <div className="flex items-center gap-4 w-full justify-center mt-1">
              <button
                type="button"
                onClick={onCancelRecording}
                className="p-2.5 text-stone-500 hover:text-dukaan-error hover:bg-stone-100 rounded-full border border-dukaan-border transition-colors text-xs"
                title="Cancel"
                aria-label="Cancel recording"
              >
                <X className="w-4 h-4" aria-hidden="true" />
              </button>

              <button
                type="button"
                onClick={onStopRecording}
                className="py-2 px-5 rounded-full bg-dukaan-primary hover:bg-dukaan-primaryDark text-white font-bold text-xs shadow-warm flex items-center gap-2 transition-all transform active:scale-95"
              >
                <Square className="w-3.5 h-3.5 fill-white" aria-hidden="true" />
                <span>Turant Bhejein (Optional)</span>
              </button>
            </div>
          </div>
        ) : isProcessing ? (
          <div className="py-4 flex flex-col items-center justify-center gap-2">
            <Loader2 className="w-8 h-8 text-dukaan-primary animate-spin" aria-hidden="true" />
            <div className="text-xs font-bold text-dukaan-text">Sharma Ji soch rahe hain...</div>
            <div className="text-[11px] text-dukaan-muted">Inventory aur order database check ho raha hai</div>
          </div>
        ) : isCallActive ? (
          <div className="flex items-center justify-between py-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-emerald-800">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>Sharma Ji sunne ke liye taiyar hain</span>
            </div>
            {onEndCall && (
              <button
                type="button"
                onClick={onEndCall}
                className="py-1.5 px-4 bg-red-600 hover:bg-red-700 active:scale-95 text-white font-bold text-xs rounded-full shadow-xs flex items-center gap-1.5"
              >
                <PhoneOff className="w-3.5 h-3.5" />
                <span>Call Band Karein</span>
              </button>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            {onStartCall ? (
              <button
                type="button"
                onClick={onStartCall}
                className="w-16 h-16 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white flex items-center justify-center shadow-warm transition-all transform active:scale-95 focus:ring-4 focus:ring-emerald-200"
                aria-label="Start voice call"
              >
                <Phone className="w-7 h-7 fill-white" aria-hidden="true" />
              </button>
            ) : (
              <button
                type="button"
                onClick={onStartRecording}
                className="w-16 h-16 rounded-full bg-dukaan-primary hover:bg-dukaan-primaryDark text-white flex items-center justify-center shadow-warm transition-all transform active:scale-95 focus:ring-4 focus:ring-orange-200"
                aria-label="Start voice recording"
              >
                <Mic className="w-8 h-8" aria-hidden="true" />
              </button>
            )}
            <div className="text-xs font-semibold text-dukaan-text">
              {onStartCall ? "Kirana Call Shuru Karein" : "Mic dabayein aur boliye"}
            </div>
            <div className="text-[11px] text-dukaan-muted">Ek baar on karein aur lagatar baatcheet karein</div>
          </div>
        )}
      </div>
    </div>
  );
}
