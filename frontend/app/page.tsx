"use client";

import React, { useState, useEffect, useCallback } from "react";
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

  // Audio Playback Hook
  const {
    isPlaying: isPlayingAudio,
    autoplayBlocked,
    currentUrl: activeAudioUrl,
    playAudio,
  } = useAudioPlayer();

  // Voice Recording Hook
  const {
    isRecording,
    duration,
    audioLevel,
    errorMessage: recorderError,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useVoiceRecorder({
    maxDurationSeconds: 60,
    onMaxDurationReached: () => {
      handleStopAndSendVoiceTurn();
    },
  });

  // Initialize Store & Session
  useEffect(() => {
    async function init() {
      try {
        const storeData = await getStore("STORE001");
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
              setCartTotal(sessDetail.total_amount || 0);
              return;
            }
          } catch {
            // Expired or not found; create fresh session
          }
        }

        const newSess = await createSession("STORE001");
        setSessionId(newSess.session_id);
        if (typeof window !== "undefined") {
          localStorage.setItem("dukaansaathi_session_id", newSess.session_id);
        }
      } catch (err) {
        console.error("Initialization failed:", err);
      }
    }
    init();
  }, []);

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
        setCartTotal(turnResponse.cart.total_amount || 0);
      }

      // 4. Play assistant audio
      if (turnResponse.audio_url) {
        const fullUrl = getAudioPlaybackUrl(turnResponse.audio_url);
        playAudio(fullUrl);
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
  }, [sessionId, stopRecording, playAudio]);

  // Handle manual cart edits
  const handleUpdateCartQuantity = async (productId: string, quantity: number) => {
    if (!sessionId) return;
    const updated = await updateCartItem(sessionId, productId, quantity);
    setCartItems(updated.current_cart || []);
    setCartTotal(updated.total_amount || 0);
  };

  const handleRemoveCartItem = async (productId: string) => {
    if (!sessionId) return;
    const updated = await removeCartItem(sessionId, productId);
    setCartItems(updated.current_cart || []);
    setCartTotal(updated.total_amount || 0);
  };

  // Final Order Confirmation Submission
  const handleConfirmOrder = async () => {
    if (!sessionId || cartItems.length === 0) return;
    const itemsPayload = cartItems.map((it) => ({
      product_id: it.product_id,
      quantity: it.quantity,
    }));
    const order = await submitOrder(sessionId, "STORE001", itemsPayload);
    setConfirmedOrder(order);
    setIsConfirmModalOpen(false);

    // Clear session from storage
    if (typeof window !== "undefined") {
      localStorage.removeItem("dukaansaathi_session_id");
    }
  };

  const handleStartNewOrder = async () => {
    setConfirmedOrder(null);
    setCartItems([]);
    setCartTotal(0);
    setMessages([]);
    const newSess = await createSession("STORE001");
    setSessionId(newSess.session_id);
    if (typeof window !== "undefined") {
      localStorage.setItem("dukaansaathi_session_id", newSess.session_id);
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
            store_id: "STORE001",
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
        setCartTotal(data.total_amount || 0);
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
            errorMessage={recorderError}
            onStartRecording={startRecording}
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
