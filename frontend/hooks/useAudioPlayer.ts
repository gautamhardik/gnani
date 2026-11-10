"use client";

/**
 * DukaanSaathi — useAudioPlayer Hook
 * Manages assistant speech playback with graceful autoplay block detection
 * and manual play/pause controls.
 */

import { useState, useRef, useEffect, useCallback } from "react";

export function useAudioPlayer() {
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [autoplayBlocked, setAutoplayBlocked] = useState<boolean>(false);
  const [currentUrl, setCurrentUrl] = useState<string | null>(null);
  const [playbackError, setPlaybackError] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const onEndedCallbackRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const audio = new Audio();
      audioRef.current = audio;

      audio.onplay = () => {
        setIsPlaying(true);
        setAutoplayBlocked(false);
      };

      audio.onpause = () => {
        setIsPlaying(false);
      };

      audio.onended = () => {
        setIsPlaying(false);
        if (onEndedCallbackRef.current) {
          const cb = onEndedCallbackRef.current;
          onEndedCallbackRef.current = null;
          cb();
        }
      };

      audio.onerror = () => {
        setIsPlaying(false);
        setPlaybackError("Failed to play assistant audio response.");
        if (onEndedCallbackRef.current) {
          const cb = onEndedCallbackRef.current;
          onEndedCallbackRef.current = null;
          cb();
        }
      };
    }

    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
        audioRef.current = null;
        onEndedCallbackRef.current = null;
      }
    };
  }, []);

  const playAudio = useCallback(async (url?: string, onEnded?: () => void): Promise<boolean> => {
    const targetUrl = url || currentUrl;
    if (!targetUrl || !audioRef.current) return false;

    setPlaybackError(null);
    setCurrentUrl(targetUrl);
    if (onEnded) {
      onEndedCallbackRef.current = onEnded;
    }

    try {
      if (audioRef.current.src !== targetUrl) {
        audioRef.current.src = targetUrl;
      }
      await audioRef.current.play();
      setAutoplayBlocked(false);
      return true;
    } catch (err: any) {
      if (err.name === "NotAllowedError" || err.name === "AutoplayBlocked") {
        // Browser autoplay restricted; user gesture required
        setAutoplayBlocked(true);
      } else {
        setPlaybackError(err.message || "Audio playback error");
      }
      setIsPlaying(false);
      if (onEndedCallbackRef.current) {
        const cb = onEndedCallbackRef.current;
        onEndedCallbackRef.current = null;
        cb();
      }
      return false;
    }
  }, [currentUrl]);

  const pauseAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  }, []);

  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      try {
        audioRef.current.currentTime = 0;
      } catch { }
      setIsPlaying(false);
      onEndedCallbackRef.current = null;
    }
  }, []);

  return {
    isPlaying,
    autoplayBlocked,
    currentUrl,
    playbackError,
    playAudio,
    pauseAudio,
    stopAudio,
  };
}

