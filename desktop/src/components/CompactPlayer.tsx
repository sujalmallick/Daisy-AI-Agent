import React, { useState, useRef } from 'react';
import { Play, Pause, SkipBack, SkipForward, Music, Maximize2, ChevronLeft } from 'lucide-react';

export interface CompactPlayerProps {
  trackTitle: string;
  trackArtist: string;
  artworkUrl: string | null;
  isPlaying: boolean;
  progressMs: number;
  durationMs: number;
  onTogglePlay: (e: React.MouseEvent) => void;
  onNext: (e: React.MouseEvent) => void;
  onPrev?: (e: React.MouseEvent) => void;
  onExpand: () => void;
  onTuck?: () => void;
}

const formatTime = (ms: number): string => {
  if (!ms || isNaN(ms) || ms <= 0) return '0:00';
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
};

export const CompactPlayer: React.FC<CompactPlayerProps> = ({
  trackTitle,
  trackArtist,
  artworkUrl,
  isPlaying,
  progressMs,
  durationMs,
  onTogglePlay,
  onNext,
  onPrev,
  onExpand,
  onTuck,
}) => {
  const [dragOffset, setDragOffset] = useState<number>(0);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const startXRef = useRef<number | null>(null);
  const hasDraggedRef = useRef<boolean>(false);

  const progressPercent = durationMs > 0
    ? Math.min(100, Math.max(0, (progressMs / durationMs) * 100))
    : 0;

  const handlePointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    startXRef.current = e.clientX;
    hasDraggedRef.current = false;
    setIsDragging(true);
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (startXRef.current === null) return;
    const dx = e.clientX - startXRef.current;
    if (Math.abs(dx) > 6) {
      hasDraggedRef.current = true;
    }
    // Only allow swiping left (towards the orb) if onTuck is provided
    if (onTuck) {
      if (dx < 0) {
        setDragOffset(Math.max(-100, dx));
      } else {
        setDragOffset(Math.min(15, dx * 0.2));
      }
    }
  };

  const handlePointerUp = () => {
    if (startXRef.current !== null && onTuck) {
      if (dragOffset < -35) {
        onTuck();
      }
    }
    startXRef.current = null;
    setIsDragging(false);
    setDragOffset(0);
  };

  const handleContainerClick = () => {
    if (hasDraggedRef.current) {
      hasDraggedRef.current = false;
      return;
    }
    onExpand();
  };

  return (
    <div
      onClick={handleContainerClick}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      className="no-drag-surface group relative flex flex-col justify-between p-2 rounded-2xl cursor-pointer select-none shadow-2xl backdrop-blur-2xl bg-[#0c0f14]/90 border border-white/10 hover:border-white/20 w-[280px] h-[74px] overflow-hidden touch-none"
      title={onTuck ? "Swipe left towards Orb to tuck, or click to expand" : "Click to expand player"}
      style={{
        boxShadow: '0 16px 36px -8px rgba(0, 0, 0, 0.8), 0 0 0 1px rgba(255, 255, 255, 0.08), inset 0 1px 1px rgba(255, 255, 255, 0.15)',
        transform: `translateX(${dragOffset}px)`,
        opacity: Math.max(0.2, 1 - Math.abs(dragOffset) / 90),
        transition: isDragging ? 'none' : 'transform 0.25s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.25s ease',
      }}
    >
      {/* Quick Tuck Arrow (visible on hover if onTuck provided) */}
      {onTuck && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onTuck();
          }}
          onPointerDown={(e) => e.stopPropagation()}
          className="opacity-0 group-hover:opacity-100 absolute -left-1 top-1/2 -translate-y-1/2 w-5 h-8 flex items-center justify-center text-zinc-400 hover:text-emerald-400 transition-opacity cursor-pointer shrink-0 z-30"
          title="Tuck into Orb"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      )}

      {/* Dynamic Ambient Blur Glow behind Album Art */}
      {artworkUrl && (
        <div
          className="absolute -left-4 -top-4 w-20 h-20 rounded-full blur-xl opacity-40 pointer-events-none transition-opacity group-hover:opacity-60"
          style={{
            backgroundImage: `url(${artworkUrl})`,
            backgroundSize: 'cover',
          }}
        />
      )}

      {/* Top Row: Artwork + Track Details + Playback Controls */}
      <div className="flex items-center gap-2.5 w-full">
        {/* Album Artwork Thumbnail */}
        <div className="relative w-9 h-9 rounded-lg overflow-hidden shrink-0 border border-white/10 bg-zinc-900 shadow-md flex items-center justify-center">
          {artworkUrl ? (
            <img
              src={artworkUrl}
              alt={trackTitle}
              className="w-full h-full object-cover"
              loading="eager"
            />
          ) : (
            <Music className="w-4 h-4 text-emerald-400/60" />
          )}

          {/* Live Audio Waves Indicator */}
          {isPlaying && (
            <div className="absolute inset-0 bg-black/40 flex items-center justify-center gap-0.5 pointer-events-none">
              <span className="w-0.5 bg-emerald-400 rounded-full animate-pulse h-2" />
              <span className="w-0.5 bg-emerald-400 rounded-full animate-pulse h-3 delay-75" />
              <span className="w-0.5 bg-emerald-400 rounded-full animate-pulse h-1.5 delay-150" />
            </div>
          )}
        </div>

        {/* Track & Artist Info */}
        <div className="flex-1 min-w-0 pr-0.5">
          <span className="block text-[11.5px] font-semibold text-white truncate tracking-tight leading-tight" title={trackTitle}>
            {trackTitle}
          </span>
          <p className="text-[10px] text-zinc-400 truncate mt-0.5 leading-tight" title={trackArtist}>
            {trackArtist}
          </p>
        </div>

        {/* Media Controls: Prev, Play/Pause, Next, Expand */}
        <div className="flex items-center gap-0.5 shrink-0 no-drag">
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (onPrev) onPrev(e);
            }}
            onPointerDown={(e) => e.stopPropagation()}
            className="w-6 h-6 rounded-full text-zinc-400 hover:text-white hover:bg-white/10 flex items-center justify-center transition cursor-pointer active:scale-90"
            title="Previous track"
          >
            <SkipBack className="w-3 h-3 fill-current" />
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onTogglePlay(e);
            }}
            onPointerDown={(e) => e.stopPropagation()}
            className="w-7 h-7 rounded-full bg-white text-black hover:bg-emerald-400 hover:text-black flex items-center justify-center transition-all cursor-pointer shadow-md active:scale-90"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <Pause className="w-3 h-3 fill-current" />
            ) : (
              <Play className="w-3 h-3 fill-current ml-0.5" />
            )}
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onNext(e);
            }}
            onPointerDown={(e) => e.stopPropagation()}
            className="w-6 h-6 rounded-full text-zinc-400 hover:text-white hover:bg-white/10 flex items-center justify-center transition cursor-pointer active:scale-90"
            title="Next track"
          >
            <SkipForward className="w-3 h-3 fill-current" />
          </button>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onExpand();
            }}
            onPointerDown={(e) => e.stopPropagation()}
            className="w-5 h-5 rounded-full text-zinc-500 hover:text-white hover:bg-white/10 flex items-center justify-center transition cursor-pointer"
            title="Expand player"
          >
            <Maximize2 className="w-2.5 h-2.5" />
          </button>
        </div>
      </div>

      {/* Bottom Row: Progress Bar + Time Stamp */}
      <div className="flex items-center gap-2 w-full pt-0.5">
        <div className="flex-1 h-[2.5px] bg-white/[0.1] rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-400 transition-all duration-300 shadow-[0_0_6px_#34d399] rounded-full"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <span className="text-[9.5px] text-zinc-400 font-mono tracking-tight shrink-0 select-none">
          {formatTime(progressMs)} / {formatTime(durationMs)}
        </span>
      </div>
    </div>
  );
};

export default CompactPlayer;
