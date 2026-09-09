import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, SkipBack, SkipForward, Shuffle, Repeat, Volume2, Music, RefreshCw } from 'lucide-react';

interface NowPlayingCardProps {
  onFoldBack: () => void;
  onToast: (msg: string, meta: string) => void;
}

interface PlaybackState {
  isPlaying: boolean;
  trackTitle: string;
  trackArtist: string;
  artworkUrl: string | null;
  progressMs: number;
  durationMs: number;
  deviceName: string;
  volume: number;
  shuffleState: boolean;
  repeatState: string;
}

export const NowPlayingCard: React.FC<NowPlayingCardProps> = ({ onFoldBack, onToast }) => {
  const [playback, setPlayback] = useState<PlaybackState>({
    isPlaying: false,
    trackTitle: 'Connecting to Spotify...',
    trackArtist: 'Pulling live MCP session',
    artworkUrl: null,
    progressMs: 0,
    durationMs: 0,
    deviceName: 'Spotify',
    volume: 50,
    shuffleState: false,
    repeatState: 'off',
  });

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const volumeDebounceRef = useRef<number | null>(null);

  const formatTime = (ms: number) => {
    if (!ms || isNaN(ms) || ms <= 0) return '0:00';
    const totalSec = Math.floor(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${min}:${sec < 10 ? '0' : ''}${sec}`;
  };

  const fetchLivePlayback = async (silent: boolean = true) => {
    if (!silent) setIsLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/playback');
      if (res.ok) {
        const data = await res.json();
        const result = data?.result;
        if (result && result.track) {
          setPlayback({
            isPlaying: !!result.is_playing,
            trackTitle: result.track,
            trackArtist: `${result.artist}${result.album ? ` • ${result.album}` : ''}`,
            artworkUrl: result.artwork_url || null,
            progressMs: result.progress_ms || 0,
            durationMs: result.duration_ms || 0,
            deviceName: result.device_name || 'Active Device',
            volume: result.volume_percent ?? 50,
            shuffleState: !!result.shuffle_state,
            repeatState: result.repeat_state || 'off',
          });
        } else {
          // No track currently active
          setPlayback((prev) => ({
            ...prev,
            isPlaying: false,
            trackTitle: 'No Track Playing',
            trackArtist: 'Spotify is idle • Say "Daisy, play music"',
            artworkUrl: null,
            progressMs: 0,
            durationMs: 0,
            deviceName: result?.device_name || 'No Active Device',
            volume: result?.volume_percent ?? prev.volume,
          }));
        }
      }
    } catch (err) {
      console.warn('Playback fetch error:', err);
    } finally {
      if (!silent) setIsLoading(false);
    }
  };

  // Poll live playback every 3 seconds while card is open
  useEffect(() => {
    fetchLivePlayback(false);
    const interval = window.setInterval(() => {
      fetchLivePlayback(true);
    }, 3000);
    return () => window.clearInterval(interval);
  }, []);

  // Smoothly increment local progress bar when playing
  useEffect(() => {
    if (!playback.isPlaying || playback.durationMs <= 0) return;
    const progressTimer = window.setInterval(() => {
      setPlayback((prev) => {
        if (!prev.isPlaying || prev.progressMs >= prev.durationMs) return prev;
        return { ...prev, progressMs: Math.min(prev.durationMs, prev.progressMs + 1000) };
      });
    }, 1000);
    return () => window.clearInterval(progressTimer);
  }, [playback.isPlaying, playback.durationMs]);

  const executeAction = async (action: string, value?: any, label?: string) => {
    try {
      let res = await fetch('http://127.0.0.1:8000/playback/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, value }),
      });

      // Fallback to /command if backend instance hasn't reloaded /playback/action yet
      if (!res.ok && res.status === 404) {
        let promptText = action;
        if (action === 'pause') promptText = 'pause';
        else if (action === 'resume' || action === 'play') promptText = 'resume';
        else if (action === 'next') promptText = 'next song';
        else if (action === 'previous') promptText = 'previous song';
        else if (action === 'volume') promptText = `volume ${value}`;

        res = await fetch('http://127.0.0.1:8000/command', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: promptText, speak_backend: false }),
        });
      }

      if (label) onToast(label, 'Spotify MCP');
      // Refresh immediately after action
      setTimeout(() => fetchLivePlayback(true), 400);
    } catch (err) {
      console.warn(`Action '${action}' failed:`, err);
    }
  };

  const togglePlay = () => {
    const nextState = !playback.isPlaying;
    setPlayback((prev) => ({ ...prev, isPlaying: nextState }));
    executeAction(nextState ? 'resume' : 'pause', null, nextState ? 'Playback Resumed' : 'Playback Paused');
  };

  const handleNext = () => {
    executeAction('next', null, 'Skipped to Next Track');
  };

  const handlePrev = () => {
    executeAction('previous', null, 'Returning to Previous Track');
  };

  const handleVolumeChange = (newVal: number) => {
    setPlayback((prev) => ({ ...prev, volume: newVal }));
    if (volumeDebounceRef.current !== null) {
      window.clearTimeout(volumeDebounceRef.current);
    }
    volumeDebounceRef.current = window.setTimeout(() => {
      executeAction('volume', newVal);
    }, 250);
  };

  const progressPercent = playback.durationMs > 0
    ? Math.min(100, Math.max(0, (playback.progressMs / playback.durationMs) * 100))
    : 0;

  return (
    <div
      onDoubleClick={(e) => {
        // Prevent folding if clicking buttons/sliders
        if ((e.target as HTMLElement).tagName !== 'BUTTON' && (e.target as HTMLElement).tagName !== 'INPUT') {
          onFoldBack();
        }
      }}
      className="w-[310px] now-playing-card p-6 flex flex-col justify-between select-none shadow-2xl transition-all duration-300"
    >
      {/* Header: NOW PLAYING & Real Connected Device Pill */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-1.5">
          <span className="text-[12px] font-bold tracking-wider text-zinc-400 uppercase">NOW PLAYING</span>
          <button
            onClick={() => fetchLivePlayback(false)}
            title="Refresh Spotify status"
            className="p-1 text-zinc-500 hover:text-zinc-300 transition cursor-pointer"
          >
            <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>

        <div className="flex items-center gap-2 bg-[#1e2329]/90 px-3 py-1.5 rounded-full border border-white/5 text-[11px] text-zinc-300 max-w-[150px] truncate" title={playback.deviceName}>
          <span className={`w-2 h-2 rounded-full ${playback.isPlaying ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
          <span className="truncate">{playback.deviceName}</span>
        </div>
      </div>

      {/* Album Cover with Vinyl Peeking & Real Artwork */}
      <div className="relative w-full aspect-square my-2 flex items-center justify-center">
        {/* Vinyl Record Behind Art */}
        <div className={`absolute right-2 w-[85%] h-[85%] rounded-full bg-[#18181b] border-4 border-[#09090b] shadow-2xl flex items-center justify-center overflow-hidden transform translate-x-4 transition-transform duration-700 ${playback.isPlaying ? 'rotate-12' : ''}`}>
          <div className="w-full h-full rounded-full border border-zinc-700/30 flex items-center justify-center">
            <div className="w-2/3 h-2/3 rounded-full border border-zinc-700/20 flex items-center justify-center">
              <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-amber-600 via-orange-500 to-amber-700 flex items-center justify-center shadow-inner">
                <div className="w-4 h-4 rounded-full bg-black" />
              </div>
            </div>
          </div>
        </div>

        {/* Album Art Front */}
        <div className="relative z-10 w-[88%] h-[88%] rounded-2xl overflow-hidden shadow-2xl border border-white/10 bg-zinc-900 mr-auto flex items-center justify-center">
          {playback.artworkUrl ? (
            <img
              src={playback.artworkUrl}
              alt={playback.trackTitle}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-zinc-800 to-zinc-950 p-4 text-center">
              <Music className="w-12 h-12 text-emerald-400/40 mb-2" />
              <span className="text-[11px] text-zinc-400 font-medium">Spotify MCP</span>
              <span className="text-[9px] text-zinc-600">Daisy Assistant</span>
            </div>
          )}

          {/* Status Badge */}
          <div className="absolute top-2.5 right-2.5 bg-black/70 backdrop-blur-md px-2 py-0.5 rounded-full text-[10px] font-semibold border flex items-center gap-1.5 transition-all">
            {playback.isPlaying ? (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-emerald-400 border-emerald-500/20">LIVE</span>
              </>
            ) : playback.trackTitle !== 'No Track Playing' ? (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                <span className="text-amber-300">PAUSED</span>
              </>
            ) : (
              <>
                <span className="w-1.5 h-1.5 rounded-full bg-zinc-500" />
                <span className="text-zinc-400">IDLE</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Track Info */}
      <div className="text-center my-3 px-1">
        <h2 className="text-lg font-bold text-white tracking-tight truncate" title={playback.trackTitle}>
          {playback.trackTitle}
        </h2>
        <p className="text-xs text-zinc-400 mt-0.5 truncate" title={playback.trackArtist}>
          {playback.trackArtist}
        </p>
      </div>

      {/* Scrubber & Timestamps */}
      <div className="my-2">
        <div className="w-full bg-[#2a2e35] h-1.5 rounded-full overflow-hidden relative">
          <div
            className="bg-emerald-400 h-full rounded-full transition-all duration-300 shadow-[0_0_8px_#34d399]"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex justify-between text-[11px] text-zinc-400 mt-1.5 font-mono">
          <span>{formatTime(playback.progressMs)}</span>
          <span>{formatTime(playback.durationMs)}</span>
        </div>
      </div>

      {/* Transport Controls (Active MCP Triggers) */}
      <div className="flex items-center justify-between px-2 my-2">
        <button
          className={`p-1 transition cursor-pointer ${playback.shuffleState ? 'text-emerald-400' : 'text-zinc-500 hover:text-zinc-300'}`}
          title="Shuffle"
        >
          <Shuffle className="w-4 h-4" />
        </button>

        <button
          onClick={handlePrev}
          className="text-zinc-300 hover:text-white transition p-1 hover:scale-110 active:scale-95 cursor-pointer"
          title="Previous Track"
        >
          <SkipBack className="w-5 h-5 fill-current" />
        </button>

        <button
          onClick={togglePlay}
          className="w-12 h-12 rounded-full bg-emerald-400 hover:bg-emerald-300 text-black flex items-center justify-center shadow-lg hover:scale-105 active:scale-95 transition cursor-pointer"
          title={playback.isPlaying ? 'Pause' : 'Play'}
        >
          {playback.isPlaying ? (
            <Pause className="w-6 h-6 fill-current" />
          ) : (
            <Play className="w-6 h-6 fill-current ml-0.5" />
          )}
        </button>

        <button
          onClick={handleNext}
          className="text-zinc-300 hover:text-white transition p-1 hover:scale-110 active:scale-95 cursor-pointer"
          title="Next Track"
        >
          <SkipForward className="w-5 h-5 fill-current" />
        </button>

        <button
          className={`p-1 transition cursor-pointer ${playback.repeatState !== 'off' ? 'text-emerald-400' : 'text-zinc-500 hover:text-zinc-300'}`}
          title={`Repeat: ${playback.repeatState}`}
        >
          <Repeat className="w-4 h-4" />
        </button>
      </div>

      {/* Volume Slider Row */}
      <div className="flex items-center gap-2.5 pt-3 mt-1 border-t border-white/5">
        <Volume2 className="w-3.5 h-3.5 text-zinc-400 flex-shrink-0" />
        <input
          type="range"
          min="0"
          max="100"
          value={playback.volume}
          onChange={(e) => handleVolumeChange(Number(e.target.value))}
          className="w-full accent-emerald-400 cursor-pointer"
        />
        <span className="text-[11px] font-mono text-zinc-400 w-7 text-right">{playback.volume}%</span>
      </div>

      {/* Fold Back Trigger */}
      <div className="mt-4 pt-2 text-center border-t border-white/[0.04]">
        <button
          onClick={onFoldBack}
          className="text-[11px] text-zinc-500 hover:text-zinc-300 transition cursor-pointer"
        >
          Fold back to Orb (or double-click)
        </button>
      </div>
    </div>
  );
};

export default NowPlayingCard;
