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
  private cachedVoices: SpeechSynthesisVoice[] = [];
  private cachedConfig: { provider?: string } | null = null;
  private lastConfigFetchTime = 0;
  /** Text currently being spoken — used by echo filter */
  public currentSpokenText = '';

  constructor() {
    this._initVoices();
  }

  public invalidateConfigCache(): void {
    this.cachedConfig = null;
    this.lastConfigFetchTime = 0;
  }

  private async _getConfig(): Promise<{ provider?: string } | null> {
    const now = Date.now();
    if (this.cachedConfig && now - this.lastConfigFetchTime < 30000) {
      return this.cachedConfig;
    }
    try {
      const cfgRes = await fetch(`${BACKEND}/voice/config`);
      if (cfgRes.ok) {
        this.cachedConfig = await cfgRes.json();
        this.lastConfigFetchTime = now;
        return this.cachedConfig;
      }
    } catch {
      // Backend not reachable
    }
    return this.cachedConfig;
  }

  private _initVoices(): void {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    const load = () => {
      const v = window.speechSynthesis.getVoices();
      if (v && v.length > 0) {
        this.cachedVoices = v;
      }
    };
    load();
    window.speechSynthesis.onvoiceschanged = load;
  }

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

    // Pause and reset audio element immediately
    if (this.audio) {
      try {
        this.audio.pause();
        this.audio.removeAttribute('src');
        this.audio.load();
      } catch {
        // Ignore errors on teardown
      }
      this.audio = null;
    }

    // Revoke any blob URL to free memory
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

    // Check cached provider config first — if disabled, fire onEnd immediately
    const cfg = await this._getConfig();
    if (cfg?.provider === 'disabled') {
      this._isSpeaking = false;
      this.currentSpokenText = '';
      onEnd?.();
      return;
    }

    // Attempt streaming synthesis from backend
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
      const streamUrl = `${BACKEND}/voice/synthesize/stream?text=${encodeURIComponent(text)}`;

      const audio = new Audio();
      this.audio = audio;

      let started = false;
      const triggerStart = () => {
        if (!started) {
          started = true;
          this._isSpeaking = true;
          onStart?.();
        }
      };

      audio.onplay = triggerStart;
      audio.onplaying = triggerStart;

      audio.onended = () => {
        this._cleanup();
        onEnd?.();
      };

      audio.onerror = (e) => {
        this._cleanup();
        onError?.(e);
        onEnd?.();
      };

      audio.src = streamUrl;
      const playPromise = audio.play();
      if (playPromise !== undefined) {
        await playPromise;
      }
      return true;

    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Barge-in cancel — expected, don't report as error
        this._isSpeaking = false;
        this.currentSpokenText = '';
        return true;
      }
      this._cleanup();
      return false;
    }
  }

  private _getFemaleVoice(): SpeechSynthesisVoice | null {
    const voices = this.cachedVoices.length > 0 ? this.cachedVoices : (typeof window !== 'undefined' && window.speechSynthesis ? window.speechSynthesis.getVoices() : []);
    if (!voices || voices.length === 0) return null;

    // Priority 1: explicitly known female voices in English
    const female = voices.find(
      (v) =>
        v.lang.startsWith('en') &&
        /(zira|jenny|aria|neerja|hazel|heera|susan|catherine|linda|eva|female|woman)/i.test(v.name)
    );
    if (female) return female;

    // Priority 2: Natural or Google voices in English that are not explicitly male
    const naturalFemale = voices.find(
      (v) =>
        v.lang.startsWith('en') &&
        !/(david|mark|george|guy|male|man)/i.test(v.name) &&
        /(natural|google|online)/i.test(v.name)
    );
    if (naturalFemale) return naturalFemale;

    // Priority 3: any English voice that is NOT known male
    const nonMale = voices.find(
      (v) =>
        v.lang.startsWith('en') &&
        !/(david|mark|george|guy|male|man)/i.test(v.name)
    );
    if (nonMale) return nonMale;

    return voices[0] || null;
  }

  private _speakWebSpeech(text: string, options: PlayOptions): void {
    const { onStart, onEnd, onError } = options;

    if (typeof window === 'undefined' || !window.speechSynthesis) {
      this._isSpeaking = false;
      this.currentSpokenText = '';
      onEnd?.();
      return;
    }

    const doSpeak = () => {
      try {
        window.speechSynthesis.cancel();
        const utt = new SpeechSynthesisUtterance(text);
        // Tune pitch and rate to ensure a pleasant, feminine tone even on fallback voices
        utt.rate = 1.04;
        utt.pitch = 1.15;

        const voice = this._getFemaleVoice();
        if (voice) {
          utt.voice = voice;
        }

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
    };

    // If voices aren't loaded yet in Chromium/WebView2, wait up to 300ms for onvoiceschanged
    const currentVoices = this.cachedVoices.length > 0 ? this.cachedVoices : window.speechSynthesis.getVoices();
    if (currentVoices.length === 0) {
      let fired = false;
      const onLoaded = () => {
        if (fired) return;
        fired = true;
        this.cachedVoices = window.speechSynthesis.getVoices();
        window.speechSynthesis.removeEventListener('voiceschanged', onLoaded);
        doSpeak();
      };
      window.speechSynthesis.addEventListener('voiceschanged', onLoaded);
      setTimeout(() => {
        if (!fired) {
          fired = true;
          window.speechSynthesis.removeEventListener('voiceschanged', onLoaded);
          this.cachedVoices = window.speechSynthesis.getVoices();
          doSpeak();
        }
      }, 300);
    } else {
      doSpeak();
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
