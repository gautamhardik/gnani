import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";

describe("useVoiceRecorder Hook Tests", () => {
  let mockStream: any;
  let activeRecorderInstance: any = null;

  beforeEach(() => {
    mockStream = {
      getTracks: vi.fn().mockReturnValue([{ stop: vi.fn() }]),
    };

    class MockMediaRecorder {
      state = "inactive";
      ondataavailable: any = null;
      onstop: any = null;
      mimeType = "audio/webm";

      static isTypeSupported = vi.fn().mockReturnValue(true);

      constructor() {
        activeRecorderInstance = this;
      }

      start() {
        this.state = "recording";
      }

      stop() {
        this.state = "inactive";
        if (this.onstop) {
          this.onstop();
        }
      }
    }

    (global as any).MediaRecorder = MockMediaRecorder;

    Object.defineProperty(global.navigator, "mediaDevices", {
      value: {
        getUserMedia: vi.fn().mockResolvedValue(mockStream),
      },
      configurable: true,
      writable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    activeRecorderInstance = null;
  });

  it("initializes in ready state", () => {
    const { result } = renderHook(() => useVoiceRecorder());
    expect(result.current.status).toBe("ready");
    expect(result.current.isRecording).toBe(false);
    expect(result.current.duration).toBe(0);
  });

  it("starts recording when permission is granted", async () => {
    const { result } = renderHook(() => useVoiceRecorder());

    let success: boolean = false;
    await act(async () => {
      success = await result.current.startRecording();
    });

    expect(success).toBe(true);
    expect(result.current.status).toBe("recording");
    expect(result.current.isRecording).toBe(true);
    expect(global.navigator.mediaDevices.getUserMedia).toHaveBeenCalled();
  });

  it("handles permission denial gracefully", async () => {
    const permError = new Error("Permission denied");
    permError.name = "NotAllowedError";

    (global.navigator.mediaDevices.getUserMedia as any).mockRejectedValueOnce(
      permError
    );

    const { result } = renderHook(() => useVoiceRecorder());

    let success: boolean = true;
    await act(async () => {
      success = await result.current.startRecording();
    });

    expect(success).toBe(false);
    expect(result.current.status).toBe("permission_denied");
    expect(result.current.errorMessage).toContain("Microphone permission was denied");
  });

  it("cancels recording and resets state", async () => {
    const { result } = renderHook(() => useVoiceRecorder());

    await act(async () => {
      await result.current.startRecording();
    });
    expect(result.current.isRecording).toBe(true);

    act(() => {
      result.current.cancelRecording();
    });

    expect(result.current.status).toBe("ready");
    expect(result.current.isRecording).toBe(false);
  });
});
