"use client";

/**
 * DukaanSaathi — useVoiceRecorder Hook
 * Reusable MediaRecorder hook with cross-browser permission handling,
 * live waveform analyzer, duration limits, and graceful cleanup.
 */

import { useState, useRef, useCallback, useEffect } from "react";

export type RecorderState =
  | "ready"
  | "recording"
  | "processing"
  | "speaking"
  | "permission_denied"
  | "error";

export interface VoiceRecordingResult {
  blob: Blob;
  mimeType: string;
  durationSeconds: number;
}

interface UseVoiceRecorderOptions {
  maxDurationSeconds?: number;
  onMaxDurationReached?: () => void;
  autoVad?: boolean;
  silenceMs?: number; // silence duration before auto-stop (default 1200ms)
  speechThreshold?: number; // audio level threshold for speech onset (default 0.035)
  silenceThreshold?: number; // audio level threshold for silence (default 0.02)
  onSilenceAutoStop?: () => void;
  noSpeechTimeoutMs?: number; // no speech timeout (default 0 - continuous)
  onNoSpeechTimeout?: () => void;
  onBargeIn?: () => void; // Blueprint sub-millisecond barge-in trigger when user interrupts agent speech
}

export function useVoiceRecorder({
  maxDurationSeconds = 60,
  onMaxDurationReached,
  autoVad = true,
  silenceMs = 1000,
  speechThreshold = 0.03,
  silenceThreshold = 0.02,
  onSilenceAutoStop,
  noSpeechTimeoutMs = 0,
  onNoSpeechTimeout,
  onBargeIn,
}: UseVoiceRecorderOptions = {}) {
  const [status, setStatus] = useState<RecorderState>("ready");
  const [duration, setDuration] = useState<number>(0);
  const [audioLevel, setAudioLevel] = useState<number>(0);
  const [hasSpoken, setHasSpoken] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const startTimeRef = useRef<number>(0);
  const hasSpokenRef = useRef<boolean>(false);
  const silenceStartRef = useRef<number | null>(null);
  const recordStartRef = useRef<number>(0);
  const noSpeechTriggeredRef = useRef<boolean>(false);
  const autoStopTriggeredRef = useRef<boolean>(false);
  const noiseFloorRef = useRef<number>(0.015);
  const peakSpeechRef = useRef<number>(0.05);

  const onSilenceAutoStopRef = useRef(onSilenceAutoStop);
  useEffect(() => {
    onSilenceAutoStopRef.current = onSilenceAutoStop;
  }, [onSilenceAutoStop]);

  const onNoSpeechTimeoutRef = useRef(onNoSpeechTimeout);
  useEffect(() => {
    onNoSpeechTimeoutRef.current = onNoSpeechTimeout;
  }, [onNoSpeechTimeout]);

  const onBargeInRef = useRef(onBargeIn);
  useEffect(() => {
    onBargeInRef.current = onBargeIn;
  }, [onBargeIn]);

  // Detect supported browser MIME types
  const getSupportedMimeType = useCallback((): string => {
    if (typeof window === "undefined" || !window.MediaRecorder) {
      return "audio/webm";
    }
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/mp4",
      "audio/wav",
    ];
    for (const c of candidates) {
      if (MediaRecorder.isTypeSupported(c)) {
        return c;
      }
    }
    return "";
  }, []);

  // Cleanup helper
  const cleanupTracksAndNodes = useCallback(() => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
      animationFrameRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== "closed") {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setAudioLevel(0);
    hasSpokenRef.current = false;
    setHasSpoken(false);
    silenceStartRef.current = null;
    autoStopTriggeredRef.current = false;
  }, []);

  useEffect(() => {
    return () => {
      cleanupTracksAndNodes();
    };
  }, [cleanupTracksAndNodes]);

  // Audio level visualizer loop and Auto-VAD monitor
  const startAudioAnalysis = (stream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;

      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;
      if (audioCtx.state === "suspended") {
        audioCtx.resume().catch(() => {});
      }
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyserRef.current = analyser;

      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      let consecutiveSpeechFrames = 0;

      const tick = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArray);

        // Focus specifically on the human voice frequency band (bins 2 to 36, ~300Hz - 3400Hz)
        let voiceSum = 0;
        const voiceBins = Math.min(36, bufferLength);
        for (let i = 2; i < voiceBins; i++) {
          voiceSum += dataArray[i];
        }
        const voiceAvg = voiceSum / Math.max(1, voiceBins - 2);
        // Normalized 0 to 1 based on voice band amplitude
        const normalized = Math.min(1, voiceAvg / 100);
        setAudioLevel(normalized);

        // Auto-VAD State Machine with Voice-Band Noise Floor Tracking
        const now = Date.now();
        const elapsed = now - recordStartRef.current;

        // Baseline noise floor calibration during initial silence (<350ms)
        if (elapsed < 350) {
          noiseFloorRef.current = Math.min(noiseFloorRef.current, Math.max(0.01, normalized));
        } else if (!hasSpokenRef.current && normalized < noiseFloorRef.current * 1.4) {
          noiseFloorRef.current = noiseFloorRef.current * 0.95 + normalized * 0.05;
        }

        const dynamicSpeechThreshold = Math.max(0.035, noiseFloorRef.current + 0.025);
        const dynamicSilenceThreshold = Math.max(0.025, noiseFloorRef.current + 0.018);

        // Blueprint Sub-millisecond Barge-In: if user speaks while agent is playing speech
        if (status === "speaking" && normalized >= dynamicSpeechThreshold) {
          if (onBargeInRef.current) {
            onBargeInRef.current();
          }
        }

        if (autoVad && !autoStopTriggeredRef.current) {
          if (!hasSpokenRef.current) {
            // Monitor for onset of user speech
            if (normalized >= dynamicSpeechThreshold) {
              consecutiveSpeechFrames++;
              if (consecutiveSpeechFrames >= 2) {
                hasSpokenRef.current = true;
                peakSpeechRef.current = normalized;
                setHasSpoken(true);
                silenceStartRef.current = null;
              }
            } else {
              consecutiveSpeechFrames = 0;
              if (noSpeechTimeoutMs && elapsed >= noSpeechTimeoutMs) {
                if (!noSpeechTriggeredRef.current) {
                  noSpeechTriggeredRef.current = true;
                  if (onNoSpeechTimeoutRef.current) {
                    onNoSpeechTimeoutRef.current();
                  }
                }
              }
            }
          } else {
            // User has spoken! Track peak voice volume
            if (normalized > peakSpeechRef.current) {
              peakSpeechRef.current = normalized;
            }

            // User is in a pause if voice-band energy falls back near noise floor or well below peak
            const silenceCutoff = Math.max(dynamicSilenceThreshold, peakSpeechRef.current * 0.35);
            const isQuiet = normalized <= silenceCutoff;

            if (isQuiet) {
              if (!silenceStartRef.current) {
                silenceStartRef.current = now;
              } else if (now - silenceStartRef.current >= silenceMs && elapsed >= 700) {
                // User paused for silenceMs! Auto-stop and trigger AI turn
                autoStopTriggeredRef.current = true;
                if (onSilenceAutoStopRef.current) {
                  onSilenceAutoStopRef.current();
                }
                return;
              }
            } else {
              // Only reset silence if speech is clearly active (avoid resetting on 1-frame mic noise)
              if (normalized > dynamicSpeechThreshold) {
                silenceStartRef.current = null;
              }
            }
          }
        }

        animationFrameRef.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      // AudioContext may fail in some locked environments
    }
  };

  const startRecording = useCallback(async () => {
    setErrorMessage(null);
    audioChunksRef.current = [];
    setDuration(0);
    hasSpokenRef.current = false;
    setHasSpoken(false);
    silenceStartRef.current = null;
    noSpeechTriggeredRef.current = false;
    autoStopTriggeredRef.current = false;
    noiseFloorRef.current = 0.015;
    peakSpeechRef.current = 0.05;
    recordStartRef.current = Date.now();

    if (typeof window === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setStatus("error");
      setErrorMessage("Microphone audio recording is not supported in this browser.");
      return false;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;
      stream.getTracks().forEach((track) => {
        track.onended = () => {
          stopRecording();
        };
      });

      const mimeType = getSupportedMimeType();
      const options: MediaRecorderOptions = mimeType ? { mimeType } : {};
      const recorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.start(100); // 100ms timeslices for smooth chunking
      setStatus("recording");
      startTimeRef.current = Date.now();

      startAudioAnalysis(stream);

      // Duration timer & max limit check
      timerIntervalRef.current = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
        setDuration(elapsed);

        if (elapsed >= maxDurationSeconds) {
          if (onMaxDurationReached) {
            onMaxDurationReached();
          }
          stopRecording();
        }
      }, 250);

      return true;
    } catch (err: any) {
      cleanupTracksAndNodes();
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        setStatus("permission_denied");
        setErrorMessage(
          "Microphone permission was denied. Please allow microphone access in your browser settings to speak your order."
        );
      } else {
        setStatus("error");
        setErrorMessage(
          err.message || "Failed to access microphone. Please check your audio settings."
        );
      }
      return false;
    }
  }, [cleanupTracksAndNodes, getSupportedMimeType, maxDurationSeconds, onMaxDurationReached]);

  const stopRecording = useCallback((): Promise<VoiceRecordingResult | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (!recorder || recorder.state === "inactive") {
        cleanupTracksAndNodes();
        setStatus("ready");
        resolve(null);
        return;
      }

      const totalDuration = Math.max(
        0.5,
        (Date.now() - startTimeRef.current) / 1000
      );

      recorder.onstop = () => {
        const mime = recorder.mimeType || "audio/webm";
        const finalBlob = new Blob(audioChunksRef.current, { type: mime });
        cleanupTracksAndNodes();

        if (finalBlob.size === 0) {
          setStatus("ready");
          resolve(null);
          return;
        }

        resolve({
          blob: finalBlob,
          mimeType: mime,
          durationSeconds: totalDuration,
        });
      };

      try {
        recorder.stop();
      } catch {
        cleanupTracksAndNodes();
        setStatus("ready");
        resolve(null);
      }
    });
  }, [cleanupTracksAndNodes]);

  const cancelRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.onstop = null;
      try {
        recorder.stop();
      } catch {}
    }
    cleanupTracksAndNodes();
    audioChunksRef.current = [];
    setDuration(0);
    setStatus("ready");
  }, [cleanupTracksAndNodes]);

  return {
    status,
    setStatus,
    isRecording: status === "recording",
    duration,
    audioLevel,
    hasSpoken,
    errorMessage,
    startRecording,
    stopRecording,
    cancelRecording,
  };
}

