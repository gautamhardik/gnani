"use client";

import React from "react";
import { Volume2, User, Bot, Sparkles, AlertCircle } from "lucide-react";
import { getAudioPlaybackUrl } from "@/lib/api";

export interface TableItemRow {
  name?: string;
  item?: string;
  category?: string;
  price?: string | number;
  rate?: string | number;
  stock?: string | number;
  quantity?: string | number;
  [key: string]: unknown;
}

export interface ConversationMessage {
  id: string;
  sender: "customer" | "assistant";
  text: string;
  audioUrl?: string | null;
  intent?: string;
  clarificationOptions?: string[] | null;
  tableData?: TableItemRow[] | null;
  tableTitle?: string | null;
  timestamp: string;
}

interface TranscriptListProps {
  messages: ConversationMessage[];
  onPlayAudio: (url: string) => void;
  isPlayingAudio: boolean;
  activeAudioUrl: string | null;
  onSelectClarification?: (option: string) => void;
  selectedLanguage?: string;
}

export function TranscriptList({
  messages,
  onPlayAudio,
  isPlayingAudio,
  activeAudioUrl,
  onSelectClarification,
  selectedLanguage = "hi-IN",
}: TranscriptListProps) {
  const isEnglish = selectedLanguage === "en-IN";
  const customerLabel = isEnglish ? "Customer" : "Grahak (ग्राहक)";
  const assistantLabel = isEnglish ? "DukaanSaathi" : "दुकान साथी";

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-center text-dukaan-muted">
        <div className="w-12 h-12 rounded-full bg-white/90 border border-dukaan-border flex items-center justify-center mb-3 shadow-warm">
          <Sparkles className="w-6 h-6 text-dukaan-primary" aria-hidden="true" />
        </div>
        <p className="text-sm font-semibold text-dukaan-text">
          {isEnglish ? "Order anything by voice" : "कुछ भी बोल कर मंगवाएं"}
        </p>
        <p className="text-xs text-dukaan-muted mt-1 max-w-xs leading-relaxed">
          {isEnglish
            ? 'Like: "Two packets of Maggi and one kilo Aashirvaad aata"'
            : "जैसे: \"दो पैकेट मैगी और एक किलो आशीर्वाद आटा दे दो\""}
        </p>
      </div>
    );
  }

  return (
    <div
      className="space-y-3.5 p-4"
      role="log"
      aria-label="Conversation Transcript"
      aria-live="polite"
    >
      {messages.map((msg) => {
        const isCustomer = msg.sender === "customer";
        const hasAudio = !isCustomer && !!msg.audioUrl;
        const fullAudioUrl = hasAudio ? getAudioPlaybackUrl(msg.audioUrl!) : null;
        const isThisPlaying =
          isPlayingAudio && fullAudioUrl && activeAudioUrl === fullAudioUrl;

        return (
          <div
            key={msg.id}
            className={`flex flex-col ${
              isCustomer ? "items-end" : "items-start"
            }`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 shadow-sm text-sm ${
                isCustomer
                  ? "bg-dukaan-primary text-white rounded-br-xs shadow-warm"
                  : "bg-white/95 backdrop-blur-sm border border-dukaan-border text-dukaan-text rounded-bl-xs shadow-warm"
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1.5 text-[11px] font-semibold tracking-tight">
                {isCustomer ? (
                  <>
                    <span className="text-white/90 font-medium">{customerLabel}</span>
                    <User className="w-3 h-3 text-white/80" aria-hidden="true" />
                  </>
                ) : (
                  <>
                    <Bot className="w-3.5 h-3.5 text-dukaan-primary" aria-hidden="true" />
                    <span className="text-stone-800 font-semibold">{assistantLabel}</span>
                  </>
                )}
                <span className={isCustomer ? "text-white/70" : "text-dukaan-muted font-normal"}>
                  • {msg.timestamp}
                </span>
              </div>

              <p className="leading-relaxed font-normal">{msg.text}</p>

              {/* In-Chat Structured Table / Bill / Inventory Widget */}
              {msg.tableData && msg.tableData.length > 0 && (
                <div className="mt-3 overflow-hidden rounded-xl border border-dukaan-border bg-dukaan-canvas shadow-xs">
                  {msg.tableTitle && (
                    <div className="px-3 py-2 bg-orange-100/70 border-b border-dukaan-border text-xs font-bold text-dukaan-primaryDark flex items-center justify-between">
                      <span>{msg.tableTitle}</span>
                      <span className="text-[10px] bg-white px-2 py-0.5 rounded-full border border-orange-200">
                        {msg.tableData.length} items
                      </span>
                    </div>
                  )}
                  <div className="max-h-56 overflow-y-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-stone-100 text-stone-600 font-semibold sticky top-0 text-[11px] border-b border-stone-200">
                        <tr>
                          <th className="py-1.5 px-2.5">Samaan (Item)</th>
                          <th className="py-1.5 px-2 text-right">Daam (Price)</th>
                          <th className="py-1.5 px-2.5 text-right">Stock / Qty</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-stone-100 text-dukaan-text">
                        {msg.tableData.map((row, idx) => (
                          <tr key={idx} className="hover:bg-orange-50/50 transition-colors">
                            <td className="py-1.5 px-2.5 font-medium leading-snug">
                              {row.name || row.item}
                              {row.category && (
                                <span className="block text-[10px] text-stone-500 font-normal">
                                  {row.category}
                                </span>
                              )}
                            </td>
                            <td className="py-1.5 px-2 text-right font-semibold text-emerald-800 whitespace-nowrap">
                              {row.price || row.rate || "-"}
                            </td>
                            <td className="py-1.5 px-2.5 text-right font-medium text-stone-700 whitespace-nowrap">
                              {row.stock || row.quantity || "-"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Clarification suggestion chips */}
              {msg.clarificationOptions && msg.clarificationOptions.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-dukaan-border/60">
                  <div className="text-[11px] font-semibold text-dukaan-primary mb-1.5 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" aria-hidden="true" />
                    <span>Chuniye ya boliye:</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {msg.clarificationOptions.map((opt, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => onSelectClarification && onSelectClarification(opt)}
                        className="text-xs bg-dukaan-canvas hover:bg-orange-50 text-dukaan-primaryDark font-medium px-2.5 py-1 rounded-full border border-orange-200 transition-colors"
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Audio playback button for assistant message */}
              {hasAudio && fullAudioUrl && (
                <div className="mt-2 pt-1.5 flex items-center justify-between border-t border-stone-100">
                  <button
                    type="button"
                    onClick={() => onPlayAudio(fullAudioUrl)}
                    className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full transition-colors ${
                      isThisPlaying
                        ? "bg-dukaan-primary text-white"
                        : "bg-dukaan-canvas hover:bg-stone-100 text-dukaan-text border border-dukaan-border"
                    }`}
                    aria-label={isThisPlaying ? "Pause voice response" : "Play voice response"}
                  >
                    <Volume2 className={`w-3.5 h-3.5 ${isThisPlaying ? "animate-pulse" : ""}`} aria-hidden="true" />
                    <span>{isThisPlaying ? "Suniye..." : "Awaz sunein"}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
