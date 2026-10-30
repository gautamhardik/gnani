"use client";

import React from "react";

interface WaveformProps {
  isRecording: boolean;
  audioLevel: number; // 0 to 1
}

export function Waveform({ isRecording, audioLevel }: WaveformProps) {
  // 12 frequency bars
  const barCount = 12;

  return (
    <div
      className="flex items-center justify-center gap-1.5 h-12 py-2"
      role="img"
      aria-label={isRecording ? "Live audio recording waveform" : "Microphone idle"}
    >
      {Array.from({ length: barCount }).map((_, idx) => {
        // Vary heights based on audioLevel and index center weight
        const centerDistance = Math.abs(idx - barCount / 2) / (barCount / 2);
        const weight = 1 - centerDistance * 0.4;
        const dynamicHeight = isRecording
          ? Math.max(8, Math.min(40, audioLevel * 45 * weight + (idx % 3) * 4))
          : 6;

        return (
          <div
            key={idx}
            className={`w-1.5 rounded-full transition-all duration-75 ${
              isRecording ? "bg-dukaan-primary" : "bg-dukaan-border"
            }`}
            style={{ height: `${dynamicHeight}px` }}
          />
        );
      })}
    </div>
  );
}

