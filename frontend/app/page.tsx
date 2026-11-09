"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Header } from "@/components/Header";
import { StoreHomeView } from "@/components/StoreHomeView";
import { VoiceOrderingView } from "@/components/VoiceOrderingView";
import { CartView } from "@/components/CartView";
import { ConfirmationModal } from "@/components/ConfirmationModal";
import { OrderSuccessView } from "@/components/OrderSuccessView";
import { ConversationMessage } from "@/components/TranscriptList";
import { Store, CartItem, Order } from "@/types/api";
import {
  getStore,
  createSession,
  getSession,
  updateCartItem,
  removeCartItem,
  sendVoiceTurn,
  getAudioPlaybackUrl,
  submitOrder,
} from "@/lib/api";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import { useAudioPlayer } from "@/hooks/useAudioPlayer";

export default function DukaanSaathiApp() {
  const [activeTab, setActiveTab] = useState<"home" | "voice" | "cart">("home");
  const [store, setStore] = useState<Store | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>("hi-IN");
  const [sessionId, setSessionId] = useState<string>("");
  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [cartTotal, setCartTotal] = useState<number>(0);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [isProcessingTurn, setIsProcessingTurn] = useState<boolean>(false);
  const [isConfirmModalOpen, setIsConfirmModalOpen] = useState<boolean>(false);
  const [confirmedOrder, setConfirmedOrder] = useState<Order | null>(null);
  const [isSubmittingOrder, setIsSubmittingOrder] = useState<boolean>(false);
  const [isCallMode, setIsCallMode] = useState<boolean>(true);
  const [callModeToast, setCallModeToast] = useState<string | null>(null);

  const isCallModeRef = useRef<boolean>(true);
  const isConfirmModalOpenRef = useRef<boolean>(false);
  const isProcessingTurnRef = useRef<boolean>(false);

  useEffect(() => {
    isCallModeRef.current = isCallMode;
  }, [isCallMode]);

  useEffect(() => {
    isConfirmModalOpenRef.current = isConfirmModalOpen;
  }, [isConfirmModalOpen]);

  useEffect(() => {
    isProcessingTurnRef.current = isProcessingTurn;
  }, [isProcessingTurn]);

  const storeId = process.env.NEXT_PUBLIC_STORE_ID || "STORE001";

  // Audio Playback Hook
  const {
    isPlaying: isPlayingAudio,
    autoplayBlocked,
    currentUrl: activeAudioUrl,
    playAudio,
    stopAudio,
  } = useAudioPlayer();

  // Voice Recording Hook with Hands-Free Auto-VAD
  const {
    isRecording,
    duration,
    audioLevel,
    hasSpoken,
    errorMessage: recorderError,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useVoiceRecorder({
    maxDurationSeconds: 60,
    autoVad: isCallMode,
    silenceMs: 1600,
    speechThreshold: 0.12,
    silenceThreshold: 0.08,
    onSilenceAutoStop: () => {
      handleStopAndSendVoiceTurn();
    },
    noSpeechTimeoutMs: 7000,
    onNoSpeechTimeout: () => {
      if (isCallModeRef.current) {
        setIsCallMode(false);
        setCallModeToast("Silence detected — Call paused. Tap mic to resume.");
        stopRecording();
      }
    },
    onMaxDurationReached: () => {
      handleStopAndSendVoiceTurn();
    },
  });

  // Initialize Store & Session
  useEffect(() => {
    async function init() {
      try {
        const storeData = await getStore(storeId);
        setStore(storeData);

        // Resume existing session if saved in localStorage, else create
        const existingSessId = typeof window !== "undefined"
          ? localStorage.getItem("dukaansaathi_session_id")
          : null;

        if (existingSessId) {
          try {
            const sessDetail = await getSession(existingSessId);
            if (sessDetail && sessDetail.status === "active") {
              setSessionId(sessDetail.session_id);
              setCartItems(sessDetail.current_cart || []);
              setCartTotal(Number(sessDetail.total_amount || 0));
              return;
            }
          } catch {
            // Expired or not found; create fresh session
          }
        }

        const newSess = await createSession(storeId);
        setSessionId(newSess.session_id);
        if (typeof window !== "undefined") {
          localStorage.setItem("dukaansaathi_session_id", newSess.session_id);
        }
      } catch (err) {
        console.error("Initialization failed:", err);
      }
    }
    init();
  }, [storeId]);

  // Handle Stop Recording & Upload Turn
  const handleStopAndSendVoiceTurn = useCallback(async () => {
    const res = await stopRecording();
    if (!res || !sessionId) return;

    setIsProcessingTurn(true);
    try {
      const ext = res.mimeType.includes("wav") ? "wav" : "webm";
      const filename = `turn_${Date.now()}.${ext}`;

      const turnResponse = await sendVoiceTurn(
        sessionId,
        res.blob,
        filename
      );

      const nowTime = new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });

      // 1. Add customer message
      const customerMsg: ConversationMessage = {
        id: `cust_${Date.now()}`,
        sender: "customer",
        text: turnResponse.transcript || "(Khali awaz / Silence)",
        timestamp: nowTime,
      };

      // 2. Add assistant message
      const assistantMsg: ConversationMessage = {
        id: `asst_${Date.now()}`,
        sender: "assistant",
        text: turnResponse.assistant_text,
        audioUrl: turnResponse.audio_url,
        intent: turnResponse.intent,
        clarificationOptions:
          turnResponse.action_details?.clarification_options,
        timestamp: nowTime,
      };

      setMessages((prev) => [...prev, customerMsg, assistantMsg]);

      // 3. Update authoritative cart state
      if (turnResponse.cart) {
        setCartItems(turnResponse.cart.items || []);
        setCartTotal(Number(turnResponse.cart.total_amount || 0));
      }

      // Check if order transitioned to AWAITING_CONFIRMATION
      if (turnResponse.session_state === "AWAITING_CONFIRMATION") {
        setIsConfirmModalOpen(true);
      }

      // 4. Play assistant audio with continuous turn-taking for hands-free Call Mode
      if (turnResponse.audio_url) {
        const fullUrl = getAudioPlaybackUrl(turnResponse.audio_url);
        playAudio(fullUrl, () => {
          if (isCallModeRef.current && !isConfirmModalOpenRef.current) {
            setTimeout(() => {
              if (isCallModeRef.current && !isProcessingTurnRef.current) {
                startRecording();
              }
            }, 250);
          }
        });
      } else if (isCallModeRef.current && !isConfirmModalOpenRef.current) {
        setTimeout(() => {
          if (isCallModeRef.current && !isProcessingTurnRef.current) {
            startRecording();
          }
        }, 250);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      const errorMsg: ConversationMessage = {
        id: `err_${Date.now()}`,
        sender: "assistant",
        text: `Error: ${msg || "Failed to process voice turn."}`,
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsProcessingTurn(false);
    }
  }, [sessionId, stopRecording, playAudio, startRecording]);

  // Handle Start Recording with Barge-in (stops TTS if speaking)
  const handleStartRecording = useCallback(async () => {
    if (isPlayingAudio) {
      stopAudio();
    }
    setCallModeToast(null);
    await startRecording();
  }, [isPlayingAudio, stopAudio, startRecording]);

  const handleToggleCallMode = useCallback(() => {
    setIsCallMode((prev) => {
      const next = !prev;
      if (next && !isRecording && !isProcessingTurn) {
        startRecording();
      }
      return next;
    });
    setCallModeToast(null);
  }, [isRecording, isProcessingTurn, startRecording]);

  // Handle manual cart edits
  const handleUpdateCartQuantity = async (productId: string, quantity: number) => {
    if (!sessionId) return;
    const updated = await updateCartItem(sessionId, productId, quantity);
    setCartItems(updated.current_cart || []);
    setCartTotal(Number(updated.total_amount || 0));
  };

  const handleRemoveCartItem = async (productId: string) => {
    if (!sessionId) return;
    const updated = await removeCartItem(sessionId, productId);
    setCartItems(updated.current_cart || []);
    setCartTotal(Number(updated.total_amount || 0));
  };

  // Final Order Confirmation Submission
  const handleConfirmOrder = async () => {
    if (!sessionId || cartItems.length === 0 || isSubmittingOrder) return;
    setIsSubmittingOrder(true);
    try {
      const itemsPayload = cartItems.map((it) => ({
        product_id: it.product_id,
        quantity: it.quantity,
      }));
      const order = await submitOrder(sessionId, storeId, itemsPayload);
      setConfirmedOrder(order);
      setIsConfirmModalOpen(false);

      // Clear session from storage
      if (typeof window !== "undefined") {
        localStorage.removeItem("dukaansaathi_session_id");
      }
    } catch (err: unknown) {
      console.error("Order submission failed:", err);
      throw err;
    } finally {
      setIsSubmittingOrder(false);
    }
  };

  const handleStartNewOrder = async () => {
    setConfirmedOrder(null);
    setCartItems([]);
    setCartTotal(0);
    setMessages([]);
    try {
      const newSess = await createSession(storeId);
      setSessionId(newSess.session_id);
      if (typeof window !== "undefined") {
        localStorage.setItem("dukaansaathi_session_id", newSess.session_id);
      }
    } catch (err) {
      console.error("Start new order session creation failed:", err);
    }
    setActiveTab("voice");
  };

  // Clarification option click: simulate customer speech
  const handleSelectClarification = async (option: string) => {
    if (!sessionId) return;
    setIsProcessingTurn(true);
    try {
      // Create a small synthesis or plain turn to process
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"}/api/v1/intelligence/process-turn`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            utterance: option,
            session_id: sessionId,
            store_id: storeId,
          }),
        }
      );
      const data = await res.json();
      const nowTime = new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });

      setMessages((prev) => [
        ...prev,
        { id: `c_${Date.now()}`, sender: "customer", text: option, timestamp: nowTime },
        {
          id: `a_${Date.now()}`,
          sender: "assistant",
          text: data.action?.message || "Added to cart",
          timestamp: nowTime,
        },
      ]);

      if (data.cart) {
        setCartItems(data.cart);
        setCartTotal(Number(data.total_amount || 0));
      }
    } catch (e: unknown) {
      console.error("Clarification error:", e);
    } finally {
      setIsProcessingTurn(false);
    }
  };

  return (
    <div className="min-h-screen bg-dukaan-canvas text-dukaan-text flex flex-col font-sans">
      {/* Header */}
      <Header
        store={store}
        selectedLanguage={selectedLanguage}
        onLanguageChange={setSelectedLanguage}
        cartCount={cartItems.length}
        activeTab={activeTab}
        onTabChange={(tab) => setActiveTab(tab)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-md w-full mx-auto">
        {confirmedOrder ? (
          <OrderSuccessView
            order={confirmedOrder}
            onNewOrder={handleStartNewOrder}
          />
        ) : activeTab === "home" ? (
          <StoreHomeView
            store={store}
            onStartOrdering={() => setActiveTab("voice")}
            cartCount={cartItems.length}
            onViewCart={() => setActiveTab("cart")}
          />
        ) : activeTab === "voice" ? (
          <VoiceOrderingView
            messages={messages}
            isRecording={isRecording}
            isProcessing={isProcessingTurn}
            duration={duration}
            audioLevel={audioLevel}
            hasSpoken={hasSpoken}
            isCallMode={isCallMode}
            onToggleCallMode={handleToggleCallMode}
            callModeToast={callModeToast}
            onDismissToast={() => setCallModeToast(null)}
            errorMessage={recorderError}
            onStartRecording={handleStartRecording}
            onStopRecording={handleStopAndSendVoiceTurn}
            onCancelRecording={cancelRecording}
            onPlayAudio={(url) => playAudio(url)}
            isPlayingAudio={isPlayingAudio}
            activeAudioUrl={activeAudioUrl}
            autoplayBlocked={autoplayBlocked}
            onSelectClarification={handleSelectClarification}
            cartItems={cartItems}
            cartTotal={cartTotal}
            onViewCart={() => setActiveTab("cart")}
          />
        ) : (
          <CartView
            items={cartItems}
            totalAmount={cartTotal}
            onUpdateQuantity={handleUpdateCartQuantity}
            onRemoveItem={handleRemoveCartItem}
            onProceedToConfirm={() => setIsConfirmModalOpen(true)}
            onStartVoice={() => setActiveTab("voice")}
          />
        )}
      </main>

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={isConfirmModalOpen}
        onClose={() => setIsConfirmModalOpen(false)}
        items={cartItems}
        totalAmount={cartTotal}
        onConfirmOrder={handleConfirmOrder}
      />
    </div>
  );
}
