import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAudioPlayer } from "@/hooks/useAudioPlayer";

describe("useAudioPlayer Hook Tests", () => {
  let playMock: any;
  let pauseMock: any;

  beforeEach(() => {
    playMock = vi.fn().mockResolvedValue(undefined);
    pauseMock = vi.fn();

    class MockAudio {
      play = playMock;
      pause = pauseMock;
      src = "";
      onplay: any = null;
      onpause: any = null;
      onended: any = null;
      onerror: any = null;
    }

    (global as any).Audio = MockAudio;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("initializes with idle playback state", () => {
    const { result } = renderHook(() => useAudioPlayer());
    expect(result.current.isPlaying).toBe(false);
    expect(result.current.autoplayBlocked).toBe(false);
  });

  it("plays audio when playAudio is invoked", async () => {
    const { result } = renderHook(() => useAudioPlayer());

    let success: boolean = false;
    await act(async () => {
      success = await result.current.playAudio("http://localhost:8000/api/v1/voice/audio/aud_1");
    });

    expect(success).toBe(true);
    expect(playMock).toHaveBeenCalled();
  });

  it("detects browser autoplay blocking and sets autoplayBlocked flag", async () => {
    const autoplayErr = new Error("Autoplay not allowed");
    autoplayErr.name = "NotAllowedError";
    playMock.mockRejectedValueOnce(autoplayErr);

    const { result } = renderHook(() => useAudioPlayer());

    let success: boolean = true;
    await act(async () => {
      success = await result.current.playAudio("http://localhost:8000/api/v1/voice/audio/aud_1");
    });

    expect(success).toBe(false);
    expect(result.current.autoplayBlocked).toBe(true);
    expect(result.current.isPlaying).toBe(false);
  });

  it("pauses audio when pauseAudio is called", () => {
    const { result } = renderHook(() => useAudioPlayer());

    act(() => {
      result.current.pauseAudio();
    });

    expect(pauseMock).toHaveBeenCalled();
  });
});
