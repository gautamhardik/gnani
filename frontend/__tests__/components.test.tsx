import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Header } from "@/components/Header";
import { CartView } from "@/components/CartView";
import { ConfirmationModal } from "@/components/ConfirmationModal";
import { StoreHomeView } from "@/components/StoreHomeView";
import { TranscriptList } from "@/components/TranscriptList";
import { Store, CartItem } from "@/types/api";

const mockStore: Store = {
  store_id: "STORE001",
  store_name: "Sharma General Store (Demo)",
  slug: "sharma-general-store-demo",
  currency: "INR",
  timezone: "Asia/Kolkata",
  is_open: true,
  opening_time: "08:00 AM",
  closing_time: "10:00 PM",
  contact_display: "Demo store",
  description: "Voice-first kirana store",
  supported_languages: ["hi-IN", "hi-en", "en-IN"],
};

const mockCartItems: CartItem[] = [
  {
    product_id: "PRD001",
    name: "Loose Wheat Flour (Atta)",
    quantity: 2,
    unit: "kg",
    unit_price: 42.0,
    subtotal: 84.0,
  },
  {
    product_id: "PRD041",
    name: "Maggi 2-Minute Masala Noodles 70g",
    quantity: 3,
    unit: "packet",
    unit_price: 14.0,
    subtotal: 42.0,
  },
];

describe("Frontend Component Tests", () => {
  it("renders Header with store title, open badge, and cart count", () => {
    render(
      <Header
        store={mockStore}
        selectedLanguage="hi-IN"
        onLanguageChange={vi.fn()}
        cartCount={2}
        activeTab="home"
        onTabChange={vi.fn()}
      />
    );

    expect(screen.getByText("Sharma General Store (Demo)")).toBeInTheDocument();
    expect(screen.getByText("Dukaan Khuli Hai")).toBeInTheDocument();
    expect(screen.getByLabelText("Cart with 2 items")).toBeInTheDocument();
  });

  it("renders StoreHomeView with welcome banner, CTA, and examples", () => {
    const startMock = vi.fn();
    render(
      <StoreHomeView
        store={mockStore}
        onStartOrdering={startMock}
        cartCount={0}
        onViewCart={vi.fn()}
      />
    );

    expect(screen.getByText(/Namaste! Sharma General Store/i)).toBeInTheDocument();
    const ctaBtn = screen.getByText("Awaaz Se Order Shuru Karein");
    expect(ctaBtn).toBeInTheDocument();

    fireEvent.click(ctaBtn);
    expect(startMock).toHaveBeenCalledTimes(1);
  });

  it("renders CartView with authoritative items, unit prices, and subtotals", () => {
    const updateMock = vi.fn();
    const removeMock = vi.fn();
    const confirmMock = vi.fn();

    render(
      <CartView
        items={mockCartItems}
        totalAmount={126.0}
        onUpdateQuantity={updateMock}
        onRemoveItem={removeMock}
        onProceedToConfirm={confirmMock}
        onStartVoice={vi.fn()}
      />
    );

    expect(screen.getByText("Loose Wheat Flour (Atta)")).toBeInTheDocument();
    expect(screen.getByText("Maggi 2-Minute Masala Noodles 70g")).toBeInTheDocument();
    expect(screen.getAllByText("₹126.00").length).toBeGreaterThan(0);

    const confirmBtn = screen.getByText("Order Confirm Karein");
    fireEvent.click(confirmBtn);
    expect(confirmMock).toHaveBeenCalledTimes(1);
  });

  it("renders ConfirmationModal with itemized list and submit button", () => {
    const confirmOrderMock = vi.fn().mockResolvedValue(undefined);
    const closeMock = vi.fn();

    render(
      <ConfirmationModal
        isOpen={true}
        onClose={closeMock}
        items={mockCartItems}
        totalAmount={126.0}
        onConfirmOrder={confirmOrderMock}
      />
    );

    expect(screen.getByText("Order Confirmation")).toBeInTheDocument();
    expect(screen.getByText(/DukaanSaathi Policy/i)).toBeInTheDocument();
    expect(screen.getByText("Haan, Order Bhejo")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Haan, Order Bhejo"));
    expect(confirmOrderMock).toHaveBeenCalledTimes(1);
  });

  it("renders TranscriptList with customer and assistant messages", () => {
    const playMock = vi.fn();
    const messages = [
      {
        id: "1",
        sender: "customer" as const,
        text: "Do packet Maggi dena",
        timestamp: "10:30 AM",
      },
      {
        id: "2",
        sender: "assistant" as const,
        text: "Humne do packet Maggi cart mein add kar diya hai.",
        audioUrl: "/api/v1/voice/audio/aud_1",
        timestamp: "10:30 AM",
      },
    ];

    render(
      <TranscriptList
        messages={messages}
        onPlayAudio={playMock}
        isPlayingAudio={false}
        activeAudioUrl={null}
      />
    );

    expect(screen.getByText("Do packet Maggi dena")).toBeInTheDocument();
    expect(
      screen.getByText("Humne do packet Maggi cart mein add kar diya hai.")
    ).toBeInTheDocument();
    expect(screen.getByText("Awaz sunein")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Awaz sunein"));
    expect(playMock).toHaveBeenCalledTimes(1);
  });
});
