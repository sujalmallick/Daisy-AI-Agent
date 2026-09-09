/**
 * Daisy TTS Client — Frontend Voice Engine
 * ==========================================
 * Single centralized client for all text-to-speech playback in the browser.
 *
 * Design principles:
 *  - Only ONE audio instance can play at a time.
 *  - `stop()` is instantaneous (< 5ms) — critical for barge-in.
 *  - Streams audio from backend `/voice/synthesize?text=...` (MP3 or WAV).
 *  - Falls back to Web Speech API if the backend is unreachable.
 *  - If provider is "disabled", fires onEnd immediately and plays nothing.
 */

const BACKEND = 'http://127.0.0.1:8000';

interface PlayOptions {
  onStart?: () => void;
  onEnd?: () => void;
  onError?: (err: unknown) => void;
}

class TTSClient {
  private audio: HTMLAudioElement | null = null;
  private currentObjectUrl: string | null = null;
  private abortController: AbortController | null = null;
  private _isSpeaking = false;
  /** Text currently being spoken — used by echo filter */
  public currentSpokenText = '';

  /** Returns true if audio is actively playing. */
  isSpeaking(): boolean {
    return this._isSpeaking;
  }

  /**
   * Stop any active TTS playback immediately.
   * Called during barge-in to cut Daisy off in < 5ms.
   */
  stop(): void {
    // Abort any in-flight synthesis fetch
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }

    // Pause and reset audio element
    if (this.audio) {
      try {
        this.audio.pause();
        this.audio.src = '';
        this.audio.load();
      } catch {
        // Ignore errors on teardown
      }
      this.audio = null;
    }

    // Revoke the blob URL to free memory
    if (this.currentObjectUrl) {
      URL.revokeObjectURL(this.currentObjectUrl);
      this.currentObjectUrl = null;
    }

    // Tell backend to stop server-side playback too (for /voice/test)
    fetch(`${BACKEND}/voice/stop`, { method: 'POST' }).catch(() => {});

    this._isSpeaking = false;
    this.currentSpokenText = '';
  }

  /**
   * Play text via the backend TTS engine.
   * Any previous audio is stopped immediately before starting.
   */
  async play(text: string, options: PlayOptions = {}): Promise<void> {
    const { onEnd } = options;
    if (!text || !text.trim()) {
      onEnd?.();
      return;
    }

    const clean = text
      .replace(/https?:\/\/\S+/g, '')
      .replace(/[*_#`~]/g, '')
      .trim();
    if (!clean) {
      onEnd?.();
      return;
    }

    // Stop any existing audio first
    this.stop();
    this._isSpeaking = true;
    this.currentSpokenText = clean;

    // Check provider config first — if disabled, fire onEnd immediately
    try {
      const cfgRes = await fetch(`${BACKEND}/voice/config`);
      if (cfgRes.ok) {
        const cfg = await cfgRes.json();
        if (cfg.provider === 'disabled') {
          this._isSpeaking = false;
          this.currentSpokenText = '';
          onEnd?.();
          return;
        }
      }
    } catch {
      // Backend not reachable, fall through to Web Speech fallback
    }

    // Attempt to synthesize from backend
    const synthesized = await this._synthesizeFromBackend(clean, options);
    if (!synthesized) {
      // Fallback to Web Speech API
      this._speakWebSpeech(clean, options);
    }
  }

  private async _synthesizeFromBackend(text: string, options: PlayOptions): Promise<boolean> {
    const { onStart, onEnd, onError } = options;

    try {
      this.abortController = new AbortController();
      const url = `${BACKEND}/voice/synthesize?text=${encodeURIComponent(text)}`;

      const res = await fetch(url, { signal: this.abortController.signal });

      if (!res.ok || res.status === 204) {
        // 204 = disabled or synthesis failure
        this._isSpeaking = false;
        this.currentSpokenText = '';
        onEnd?.();
        return true; // "Handled" — don't fallback to web speech for disabled state
      }

      const blob = await res.blob();
      if (!blob || blob.size === 0) {
        return false;
      }

      this.abortController = null;
      const objectUrl = URL.createObjectURL(blob);
      this.currentObjectUrl = objectUrl;

      const audio = new Audio(objectUrl);
      this.audio = audio;

      audio.onplay = () => {
        onStart?.();
      };

      audio.onended = () => {
        this._cleanup();
        onEnd?.();
      };

      audio.onerror = (e) => {
        this._cleanup();
        onError?.(e);
        onEnd?.();
      };

      await audio.play();
      return true;

    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Barge-in cancel — expected, don't report as error
        this._isSpeaking = false;
        this.currentSpokenText = '';
        return true;
      }
      return false;
    }
  }

  private _speakWebSpeech(text: string, options: PlayOptions): void {
    const { onStart, onEnd, onError } = options;

    if (typeof window === 'undefined' || !window.speechSynthesis) {
      this._isSpeaking = false;
      this.currentSpokenText = '';
      onEnd?.();
      return;
    }

    try {
      window.speechSynthesis.cancel();
      const utt = new SpeechSynthesisUtterance(text);
      utt.rate = 1.05;
      utt.pitch = 1.02;

      // Pick best available English voice — prefer female/neural
      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(
        (v) =>
          v.lang.startsWith('en') &&
          (v.name.includes('Natural') ||
            v.name.includes('Jenny') ||
            v.name.includes('Zira') ||
            v.name.includes('Aria') ||
            v.name.includes('Google') ||
            v.name.includes('Female'))
      ) ?? voices.find((v) => v.lang.startsWith('en'));

      if (preferred) utt.voice = preferred;

      utt.onstart = () => onStart?.();
      utt.onend = () => {
        this._isSpeaking = false;
        this.currentSpokenText = '';
        onEnd?.();
      };
      utt.onerror = (e) => {
        this._isSpeaking = false;
        this.currentSpokenText = '';
        onError?.(e);
        onEnd?.();
      };

      window.speechSynthesis.speak(utt);
    } catch (e) {
      this._isSpeaking = false;
      this.currentSpokenText = '';
      onError?.(e);
      onEnd?.();
    }
  }

  private _cleanup(): void {
    if (this.currentObjectUrl) {
      URL.revokeObjectURL(this.currentObjectUrl);
      this.currentObjectUrl = null;
    }
    this.audio = null;
    this._isSpeaking = false;
    this.currentSpokenText = '';
  }
}

/** Single shared instance — import this everywhere. */
export const ttsClient = new TTSClient();
