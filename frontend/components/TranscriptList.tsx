"use client";

import React from "react";
import { Volume2, User, Bot, Sparkles, AlertCircle } from "lucide-react";
import { getAudioPlaybackUrl } from "@/lib/api";

export interface ConversationMessage {
  id: string;
  sender: "customer" | "assistant";
  text: string;
  audioUrl?: string | null;
  intent?: string;
  clarificationOptions?: string[] | null;
  timestamp: string;
}

interface TranscriptListProps {
  messages: ConversationMessage[];
  onPlayAudio: (url: string) => void;
  isPlayingAudio: boolean;
  activeAudioUrl: string | null;
  onSelectClarification?: (option: string) => void;
}

export function TranscriptList({
  messages,
  onPlayAudio,
  isPlayingAudio,
  activeAudioUrl,
  onSelectClarification,
}: TranscriptListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-6 text-center text-dukaan-muted">
        <div className="w-12 h-12 rounded-full bg-dukaan-card border border-dukaan-border flex items-center justify-center mb-3 shadow-warm">
          <Sparkles className="w-6 h-6 text-dukaan-primary" aria-hidden="true" />
        </div>
        <p className="text-sm font-medium text-dukaan-text">
          Kuch bhi bol kar mangwayein
        </p>
        <p className="text-xs text-dukaan-muted mt-1 max-w-xs">
          Jaise: &ldquo;Do packet Maggi aur ek kilo Aashirvaad aata dena&rdquo;
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
                  ? "bg-dukaan-primary text-white rounded-br-xs"
                  : "bg-dukaan-card border border-dukaan-border text-dukaan-text rounded-bl-xs"
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1 text-[11px] opacity-75 font-medium">
                {isCustomer ? (
                  <>
                    <span>Aap (You)</span>
                    <User className="w-3 h-3" aria-hidden="true" />
                  </>
                ) : (
                  <>
                    <Bot className="w-3 h-3 text-dukaan-primary" aria-hidden="true" />
                    <span>DukaanSaathi</span>
                  </>
                )}
                <span>• {msg.timestamp}</span>
              </div>

              <p className="leading-relaxed font-normal">{msg.text}</p>

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
