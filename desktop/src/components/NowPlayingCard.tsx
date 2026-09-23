import React, { useRef } from 'react';
import { Play, Pause, SkipBack, SkipForward, Shuffle, Repeat, Volume2, Music, RefreshCw, Minimize2 } from 'lucide-react';

export interface PlaybackState {
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
  uri?: string;
}

export interface NowPlayingCardProps {
  playback: PlaybackState;
  onFoldBack: () => void;
  onToast: (msg: string, meta: string) => void;
  onTogglePlay: () => void;
  onNext: () => void;
  onPrev: () => void;
  onToggleShuffle: () => void;
  onToggleRepeat: () => void;
  onVolumeChange: (val: number) => void;
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const NowPlayingCard: React.FC<NowPlayingCardProps> = ({
  playback,
  onFoldBack,
  onToast,
  onTogglePlay,
  onNext,
  onPrev,
  onToggleShuffle,
  onToggleRepeat,
  onVolumeChange,
  onRefresh,
  isLoading = false,
}) => {
  const volumeDebounceRef = useRef<number | null>(null);

  const formatTime = (ms: number) => {
    if (!ms || isNaN(ms) || ms <= 0) return '0:00';
    const totalSec = Math.floor(ms / 1000);
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    return `${min}:${sec < 10 ? '0' : ''}${sec}`;
  };

  const handleVolumeInput = (val: number) => {
    onVolumeChange(val);
    if (volumeDebounceRef.current !== null) {
      window.clearTimeout(volumeDebounceRef.current);
    }
    volumeDebounceRef.current = window.setTimeout(() => {
      onToast(`Volume set to ${val}%`, 'Spotify MCP');
    }, 400);
  };

  const progressPercent = playback.durationMs > 0
    ? Math.min(100, Math.max(0, (playback.progressMs / playback.durationMs) * 100))
    : 0;

  return (
    <div
      className="no-drag-surface w-[310px] now-playing-card p-5 flex flex-col justify-between select-none shadow-2xl backdrop-blur-2xl bg-[#0c0f14]/90 border border-white/10 rounded-3xl transition-all duration-300"
      style={{
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.95), 0 0 0 1px rgba(255, 255, 255, 0.08), inset 0 1px 1px rgba(255, 255, 255, 0.15)',
      }}
    >
      {/* Header: NOW PLAYING & Device Pill & Close Button */}
      <div className="no-drag-surface flex items-center justify-between mb-3.5">
        <div className="flex items-center gap-1.5 no-drag">
          <span className="text-[11px] font-bold tracking-wider text-zinc-400 uppercase">NOW PLAYING</span>
          {onRefresh && (
            <button
              onClick={onRefresh}
              title="Refresh Spotify status"
              className="p-1 text-zinc-500 hover:text-zinc-300 transition cursor-pointer"
            >
              <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin text-emerald-400' : ''}`} />
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 no-drag">
          <div
            className="flex items-center gap-1.5 bg-[#1e2329]/90 px-2.5 py-1 rounded-full border border-white/5 text-[10px] text-zinc-300 max-w-[130px] truncate"
            title={playback.deviceName}
          >
            <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${playback.isPlaying ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            <span className="truncate">{playback.deviceName}</span>
          </div>

          <button
            onClick={onFoldBack}
            className="w-7 h-7 rounded-full bg-white/5 hover:bg-white/15 text-zinc-400 hover:text-white flex items-center justify-center transition cursor-pointer"
            title="Fold back to compact player"
          >
            <Minimize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Album Cover with Vinyl Peeking */}
      <div className="relative w-full aspect-square my-1.5 flex items-center justify-center">
        {/* Vinyl Record Behind Art */}
        <div
          className={`absolute right-1 w-[85%] h-[85%] rounded-full bg-[#18181b] border-4 border-[#09090b] shadow-2xl flex items-center justify-center overflow-hidden transform translate-x-3.5 transition-transform duration-700 ${
            playback.isPlaying ? 'rotate-12' : ''
          }`}
        >
          <div className="w-full h-full rounded-full border border-zinc-700/30 flex items-center justify-center">
            <div className="w-2/3 h-2/3 rounded-full border border-zinc-700/20 flex items-center justify-center">
              <div className="w-14 h-14 rounded-full bg-gradient-to-tr from-emerald-600 via-teal-500 to-emerald-700 flex items-center justify-center shadow-inner">
                <div className="w-3.5 h-3.5 rounded-full bg-black" />
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
              <Music className="w-10 h-10 text-emerald-400/40 mb-1.5" />
              <span className="text-[11px] text-zinc-400 font-medium">Spotify MCP</span>
              <span className="text-[9px] text-zinc-600">Daisy Assistant</span>
            </div>
          )}

          {/* Status Badge */}
          <div className="absolute top-2 right-2 bg-black/70 backdrop-blur-md px-2 py-0.5 rounded-full text-[9px] font-semibold border flex items-center gap-1.5">
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
      <div className="text-center my-2.5 px-1">
        <h2 className="text-base font-bold text-white tracking-tight truncate" title={playback.trackTitle}>
          {playback.trackTitle}
        </h2>
        <p className="text-xs text-zinc-400 mt-0.5 truncate" title={playback.trackArtist}>
          {playback.trackArtist}
        </p>
      </div>

      {/* Scrubber & Timestamps */}
      <div className="my-1.5">
        <div className="w-full bg-[#2a2e35] h-1.5 rounded-full overflow-hidden relative">
          <div
            className="bg-emerald-400 h-full rounded-full transition-all duration-300 shadow-[0_0_8px_#34d399]"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-zinc-400 mt-1 font-mono">
          <span>{formatTime(playback.progressMs)}</span>
          <span>{formatTime(playback.durationMs)}</span>
        </div>
      </div>

      {/* Transport Controls */}
      <div className="flex items-center justify-between px-1 my-1.5">
        <button
          onClick={onToggleShuffle}
          className={`p-1.5 transition cursor-pointer ${playback.shuffleState ? 'text-emerald-400' : 'text-zinc-500 hover:text-zinc-300'}`}
          title="Shuffle"
        >
          <Shuffle className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={onPrev}
          className="text-zinc-300 hover:text-white transition p-1 hover:scale-110 active:scale-95 cursor-pointer"
          title="Previous Track"
        >
          <SkipBack className="w-4 h-4 fill-current" />
        </button>

        <button
          onClick={onTogglePlay}
          className="w-11 h-11 rounded-full bg-emerald-400 hover:bg-emerald-300 text-black flex items-center justify-center shadow-lg hover:scale-105 active:scale-95 transition cursor-pointer"
          title={playback.isPlaying ? 'Pause' : 'Play'}
        >
          {playback.isPlaying ? (
            <Pause className="w-5 h-5 fill-current" />
          ) : (
            <Play className="w-5 h-5 fill-current ml-0.5" />
          )}
        </button>

        <button
          onClick={onNext}
          className="text-zinc-300 hover:text-white transition p-1 hover:scale-110 active:scale-95 cursor-pointer"
          title="Next Track"
        >
          <SkipForward className="w-4 h-4 fill-current" />
        </button>

        <button
          onClick={onToggleRepeat}
          className={`p-1.5 transition cursor-pointer ${playback.repeatState !== 'off' ? 'text-emerald-400' : 'text-zinc-500 hover:text-zinc-300'}`}
          title={`Repeat: ${playback.repeatState}`}
        >
          <Repeat className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Volume Slider Row */}
      <div className="flex items-center gap-2 pt-2.5 mt-0.5 border-t border-white/5">
        <Volume2 className="w-3.5 h-3.5 text-zinc-400 shrink-0" />
        <input
          type="range"
          min="0"
          max="100"
          value={playback.volume}
          onChange={(e) => handleVolumeInput(Number(e.target.value))}
          className="w-full accent-emerald-400 cursor-pointer"
        />
        <span className="text-[10px] font-mono text-zinc-400 w-6 text-right">{playback.volume}%</span>
      </div>

      {/* Fold Back Trigger */}
      <div className="mt-2.5 pt-1.5 text-center border-t border-white/[0.04]">
        <button
          onClick={onFoldBack}
          className="text-[10px] text-zinc-500 hover:text-zinc-300 transition cursor-pointer"
        >
          Fold back to compact
        </button>
      </div>
    </div>
  );
};

export default NowPlayingCard;
