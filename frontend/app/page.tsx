"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Header } from "@/components/Header";
import { StoreHomeView } from "@/components/StoreHomeView";
import { VoiceOrderingView } from "@/components/VoiceOrderingView";
import { CartView } from "@/components/CartView";
import { ConfirmationModal } from "@/components/ConfirmationModal";
import { OrderSuccessView } from "@/components/OrderSuccessView";
import { OrderHistoryView } from "@/components/OrderHistoryView";
import { ConversationMessage } from "@/components/TranscriptList";
import { Store, CartItem, Order } from "@/types/api";
import {
  getStore,
  createSession,
  updateCartItem,
  removeCartItem,
  sendVoiceTurn,
  getAudioPlaybackUrl,
  getAgentGreeting,
  submitOrder,
} from "@/lib/api";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import { useAudioPlayer } from "@/hooks/useAudioPlayer";

export default function DukaanSaathiApp() {
  const [activeTab, setActiveTab] = useState<"home" | "voice" | "cart" | "history">("home");
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
  const [isCallActive, setIsCallActive] = useState<boolean>(false);
  const [callModeToast, setCallModeToast] = useState<string | null>(null);

  const isCallModeRef = useRef<boolean>(true);
  const isCallActiveRef = useRef<boolean>(false);
  const isConfirmModalOpenRef = useRef<boolean>(false);
  const isProcessingTurnRef = useRef<boolean>(false);
  const confirmedOrderRef = useRef<Order | null>(null);

  useEffect(() => {
    isCallModeRef.current = isCallMode;
  }, [isCallMode]);

  useEffect(() => {
    isCallActiveRef.current = isCallActive;
  }, [isCallActive]);

  useEffect(() => {
    isConfirmModalOpenRef.current = isConfirmModalOpen;
  }, [isConfirmModalOpen]);

  useEffect(() => {
    isProcessingTurnRef.current = isProcessingTurn;
  }, [isProcessingTurn]);

  useEffect(() => {
    confirmedOrderRef.current = confirmedOrder;
  }, [confirmedOrder]);

  // Clean session & messages on fresh page load or refresh
  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        localStorage.removeItem("dukaansaathi_last_messages");
        localStorage.removeItem("dukaansaathi_session_id");
      } catch {}
    }
  }, []);

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
    autoVad: true,
    silenceMs: 1400,
    speechThreshold: 0.03,
    silenceThreshold: 0.02,
    onSilenceAutoStop: () => {
      handleStopAndSendVoiceTurn();
    },
    noSpeechTimeoutMs: 0, // Keep continuous listening open without auto-pausing
    onNoSpeechTimeout: () => {},
    onBargeIn: () => {
      if (isPlayingAudio) {
        stopAudio();
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

        // Always start with a fresh empty cart on page load / refresh
        if (typeof window !== "undefined") {
          localStorage.removeItem("dukaansaathi_session_id");
        }

        const newSess = await createSession(storeId);
        setSessionId(newSess.session_id);
        setCartItems([]);
        setCartTotal(0);
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

      const isSilenceTurn =
        !turnResponse.transcript ||
        turnResponse.transcript.trim() === "" ||
        turnResponse.audio_status === "skipped_silence" ||
        turnResponse.assistant_text?.includes("sun nahi paye") ||
        turnResponse.assistant_text === "(Khali awaz / Silence)";

      if (!isSilenceTurn) {
        // 1. Add customer message
        const customerMsg: ConversationMessage = {
          id: `cust_${Date.now()}`,
          sender: "customer",
          text: turnResponse.transcript,
          timestamp: nowTime,
        };

        // 2. Add assistant message (with optional table / bill / inventory widget)
        const assistantMsg: ConversationMessage = {
          id: `asst_${Date.now()}`,
          sender: "assistant",
          text: turnResponse.assistant_text,
          audioUrl: turnResponse.audio_url,
          intent: turnResponse.intent,
          clarificationOptions:
            turnResponse.action_details?.clarification_options,
          tableData: turnResponse.table_data,
          tableTitle: turnResponse.table_title,
          timestamp: nowTime,
        };

        setMessages((prev) => [...prev, customerMsg, assistantMsg]);
      }

      // 3. Update authoritative cart state
      if (turnResponse.cart) {
        setCartItems(turnResponse.cart.items || []);
        setCartTotal(Number(turnResponse.cart.total_amount || 0));
      }

      // Check if order transitioned to AWAITING_CONFIRMATION
      if (turnResponse.session_state === "AWAITING_CONFIRMATION") {
        setIsConfirmModalOpen(true);
      }

      // Check if order was placed directly via voice command
      if (turnResponse.session_state === "ORDER_PLACED" || turnResponse.order) {
        setIsConfirmModalOpen(false);
        if (turnResponse.order) {
          setConfirmedOrder(turnResponse.order);
          confirmedOrderRef.current = turnResponse.order;
          setActiveTab("home");
          if (typeof window !== "undefined") {
            try {
              const oldHist = JSON.parse(
                localStorage.getItem("dukaansaathi_order_history") || "[]"
              );
              oldHist.push({
                order_id: turnResponse.order.order_id,
                session_id: sessionId,
              });
              localStorage.setItem(
                "dukaansaathi_order_history",
                JSON.stringify(oldHist)
              );
            } catch {}
            localStorage.removeItem("dukaansaathi_session_id");
          }
        }
      }

      // 4. Play assistant audio with continuous turn-taking for hands-free Call Mode
      if (turnResponse.audio_url) {
        const fullUrl = getAudioPlaybackUrl(turnResponse.audio_url);
        playAudio(fullUrl, () => {
          if ((isCallActiveRef.current || isCallModeRef.current) && !confirmedOrderRef.current) {
            setTimeout(() => {
              if ((isCallActiveRef.current || isCallModeRef.current) && !isProcessingTurnRef.current && !confirmedOrderRef.current) {
                startRecording();
              }
            }, 250);
          }
        });
      } else if ((isCallActiveRef.current || isCallModeRef.current) && !confirmedOrderRef.current) {
        setTimeout(() => {
          if ((isCallActiveRef.current || isCallModeRef.current) && !isProcessingTurnRef.current && !confirmedOrderRef.current) {
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

  // Start continuous Hands-Free Voice Call with proactive greeting
  const handleStartCall = useCallback(async () => {
    if (isPlayingAudio) {
      stopAudio();
    }
    setIsCallActive(true);
    isCallActiveRef.current = true;
    setIsCallMode(true);
    isCallModeRef.current = true;

    try {
      const greeting = await getAgentGreeting();
      const nowTime = new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      });

      const welcomeMsg: ConversationMessage = {
        id: `greet_${Date.now()}`,
        sender: "assistant",
        text: greeting.text,
        audioUrl: greeting.audio_url || undefined,
        timestamp: nowTime,
      };
      setMessages((prev) => [...prev, welcomeMsg]);

      if (greeting.audio_url) {
        const fullUrl = getAudioPlaybackUrl(greeting.audio_url);
        playAudio(fullUrl, () => {
          if (isCallActiveRef.current && !confirmedOrderRef.current) {
            setTimeout(() => {
              if (isCallActiveRef.current && !isProcessingTurnRef.current && !confirmedOrderRef.current) {
                startRecording();
              }
            }, 200);
          }
        });
      } else {
        setTimeout(() => {
          if (isCallActiveRef.current && !isProcessingTurnRef.current && !confirmedOrderRef.current) {
            startRecording();
          }
        }, 200);
      }
    } catch {
      startRecording();
    }
  }, [isPlayingAudio, stopAudio, playAudio, startRecording]);

  // End continuous Hands-Free Voice Call
  const handleEndCall = useCallback(() => {
    setIsCallActive(false);
    isCallActiveRef.current = false;
    stopAudio();
    cancelRecording();
  }, [stopAudio, cancelRecording]);

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
      confirmedOrderRef.current = order;
      setIsConfirmModalOpen(false);
      setActiveTab("home");

      // Persist to order history list
      if (typeof window !== "undefined") {
        try {
          const oldHist = JSON.parse(localStorage.getItem("dukaansaathi_order_history") || "[]");
          oldHist.push({ order_id: order.order_id, session_id: sessionId });
          localStorage.setItem("dukaansaathi_order_history", JSON.stringify(oldHist));
        } catch {}
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
    confirmedOrderRef.current = null;
    setCartItems([]);
    setCartTotal(0);
    setMessages([]);
    if (typeof window !== "undefined") {
      localStorage.removeItem("dukaansaathi_last_messages");
    }
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
        {activeTab === "history" ? (
          <OrderHistoryView
            onBackToOrder={() => setActiveTab("voice")}
          />
        ) : activeTab === "cart" ? (
          <CartView
            items={cartItems}
            totalAmount={cartTotal}
            onUpdateQuantity={handleUpdateCartQuantity}
            onRemoveItem={handleRemoveCartItem}
            onProceedToConfirm={() => setIsConfirmModalOpen(true)}
            onStartVoice={() => setActiveTab("voice")}
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
            isCallActive={isCallActive}
            onStartCall={handleStartCall}
            onEndCall={handleEndCall}
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
            confirmedOrder={confirmedOrder}
            onViewOrderReceipt={() => setActiveTab("home")}
            selectedLanguage={selectedLanguage}
          />
        ) : confirmedOrder ? (
          <OrderSuccessView
            order={confirmedOrder}
            onNewOrder={handleStartNewOrder}
            onViewChatHistory={() => setActiveTab("voice")}
          />
        ) : (
          <StoreHomeView
            store={store}
            onStartOrdering={() => {
              setActiveTab("voice");
              handleStartCall();
            }}
            cartCount={cartItems.length}
            onViewCart={() => setActiveTab("cart")}
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
