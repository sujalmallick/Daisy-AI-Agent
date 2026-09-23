import React, { useEffect, useRef, useCallback } from 'react';
import { Mic, Settings, MessageSquare, Maximize2, Music } from 'lucide-react';
import { startDragWindow, moveWindowBy } from '../utils/windowManager';

export type OrbStateType = 'idle' | 'listening' | 'thinking' | 'executing' | 'speaking' | 'error';
export type ThemeType = 'glassmorphism' | 'sleek' | 'cyberpunk' | 'aurora';

export interface FloatingOrbProps {
  orbState: OrbStateType;
  theme: ThemeType;
  onActivate: () => void;
  onOpenSettings?: () => void;
  onToggleTextInput?: () => void;
  onOpenDashboard?: () => void;
  isAmbientListening?: boolean;
  assistantName?: string;
  isQuickInputOpen?: boolean;
  isToastVisible?: boolean;
  onOpenWindowMode?: () => void;
  disableDrag?: boolean;
  onToggleMusic?: () => void;
  isMusicActive?: boolean;
  isPlayerTucked?: boolean;
}

const STATE_COLORS: Record<OrbStateType, Record<string, { r: number; g: number; b: number; hex: string }> | { all: { r: number; g: number; b: number; hex: string } }> = {
  idle: {
    glassmorphism: { r: 29, g: 185, b: 84, hex: '#1db954' },
    sleek: { r: 230, g: 235, b: 245, hex: '#f4f4f5' },
    cyberpunk: { r: 6, g: 182, b: 212, hex: '#06b6d4' },
    aurora: { r: 129, g: 140, b: 248, hex: '#818cf8' },
  },
  listening: {
    all: { r: 56, g: 189, b: 248, hex: '#38bdf8' },
  },
  thinking: {
    all: { r: 168, g: 85, b: 247, hex: '#a855f7' },
  },
  executing: {
    all: { r: 251, g: 146, b: 60, hex: '#fb923c' },
  },
  speaking: {
    all: { r: 45, g: 212, b: 191, hex: '#2dd4bf' },
  },
  error: {
    all: { r: 244, g: 63, b: 94, hex: '#f43f5e' },
  },
};

export const FloatingOrb: React.FC<FloatingOrbProps> = ({
  orbState,
  theme,
  onActivate,
  onOpenSettings,
  onToggleTextInput,
  isAmbientListening = true,
  assistantName = 'Daisy',
  isQuickInputOpen = false,
  isToastVisible = false,
  onOpenWindowMode,
  disableDrag = false,
  onToggleMusic,
  isMusicActive = false,
  isPlayerTucked = false,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const getColor = useCallback(() => {
    if (orbState === 'idle') {
      const idleMap = STATE_COLORS.idle as Record<string, { r: number; g: number; b: number; hex: string }>;
      return idleMap[theme] || idleMap.glassmorphism;
    }
    const stateObj = STATE_COLORS[orbState] as { all: { r: number; g: number; b: number; hex: string } };
    return stateObj.all;
  }, [orbState, theme]);

  const colorRef = useRef(getColor());
  useEffect(() => {
    colorRef.current = getColor();
  }, [getColor]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animTime = 0;
    let animFrameId: number;

    const render = () => {
      const col = colorRef.current;
      animTime += 0.024;

      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const cx = w / 2;
      const cy = h / 2;
      const radius = 54;

      // Outer radial glow gradient
      const grad = ctx.createRadialGradient(
        cx + Math.sin(animTime) * 8,
        cy + Math.cos(animTime * 0.9) * 8,
        3,
        cx,
        cy,
        radius
      );

      grad.addColorStop(0, 'rgba(255, 255, 255, 0.98)');
      grad.addColorStop(0.32, `rgba(${col.r}, ${col.g}, ${col.b}, 0.9)`);
      grad.addColorStop(0.72, `rgba(${Math.max(col.r - 40, 5)}, ${Math.max(col.g - 40, 5)}, ${Math.max(col.b - 40, 5)}, 0.92)`);
      grad.addColorStop(1, '#040508');

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(cx, cy, radius, 0, Math.PI * 2);
      ctx.fill();

      // Fluid orbital light droplets
      for (let i = 0; i < 3; i++) {
        ctx.beginPath();
        const angle = animTime * 0.9 + (i * Math.PI * 2) / 3;
        const dist = 18 + Math.sin(animTime * 1.6 + i) * 6;
        const bx = cx + Math.cos(angle) * dist;
        const by = cy + Math.sin(angle) * dist;

        const bGrad = ctx.createRadialGradient(bx, by, 2, bx, by, 25);
        bGrad.addColorStop(0, 'rgba(255, 255, 255, 0.55)');
        bGrad.addColorStop(0.5, `rgba(${col.r}, ${col.g}, ${col.b}, 0.35)`);
        bGrad.addColorStop(1, 'transparent');

        ctx.fillStyle = bGrad;
        ctx.arc(bx, by, 25, 0, Math.PI * 2);
        ctx.fill();
      }

      animFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animFrameId);
    };
  }, []);

  const dragStartRef = useRef<{ x: number; y: number; time: number; lastX: number; lastY: number } | null>(null);
  const isDraggingRef = useRef<boolean>(false);

  const handleOrbPointerDown = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    try {
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    } catch {}
    dragStartRef.current = { x: e.screenX, y: e.screenY, time: Date.now(), lastX: e.screenX, lastY: e.screenY };
    isDraggingRef.current = false;
  };

  const handleOrbPointerMove = (e: React.PointerEvent) => {
    if (!dragStartRef.current) return;
    const totalDx = e.screenX - dragStartRef.current.x;
    const totalDy = e.screenY - dragStartRef.current.y;
    if (!isDraggingRef.current && Math.hypot(totalDx, totalDy) > 5) {
      isDraggingRef.current = true;
      if (!disableDrag) {
        startDragWindow();
      }
    }
    if (isDraggingRef.current && !disableDrag) {
      const stepDx = e.screenX - dragStartRef.current.lastX;
      const stepDy = e.screenY - dragStartRef.current.lastY;
      dragStartRef.current.lastX = e.screenX;
      dragStartRef.current.lastY = e.screenY;
      if (stepDx !== 0 || stepDy !== 0) {
        moveWindowBy(stepDx, stepDy);
      }
    }
  };

  const handleOrbPointerUp = (e: React.PointerEvent) => {
    if (e.button !== 0) return;
    try {
      (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {}
    if (dragStartRef.current && !isDraggingRef.current) {
      const elapsed = Date.now() - dragStartRef.current.time;
      // An intentional click is between 40ms and 800ms
      if (elapsed >= 40 && elapsed <= 800) {
        onActivate();
      }
    }
    dragStartRef.current = null;
    isDraggingRef.current = false;
  };

  const currentColor = getColor();

  return (
    <div
      className="relative flex flex-col items-center justify-center select-none w-[170px] h-[170px] shrink-0 p-0 overflow-visible"
    >
      {/* 1. Top Status Badge (Never cut off, clean compact pill) */}
      <div className={`mb-1.5 pointer-events-none transition-all duration-300 ${isToastVisible ? 'opacity-0 scale-95' : 'opacity-100 scale-100'}`}>
        <div className="px-2.5 py-0.5 rounded-full bg-black/90 border border-white/15 backdrop-blur-md flex items-center gap-1.5 text-[9.5px] font-semibold text-white shadow-xl whitespace-nowrap">
          <span
            className="w-1.5 h-1.5 rounded-full animate-pulse flex-shrink-0"
            style={{ backgroundColor: currentColor.hex }}
          />
          <span className="tracking-wide">
            {orbState === 'listening'
              ? 'Listening...'
              : orbState === 'thinking'
              ? 'Thinking...'
              : orbState === 'executing'
              ? 'Executing...'
              : orbState === 'speaking'
              ? 'Speaking...'
              : orbState === 'error'
              ? 'Error'
              : isAmbientListening
              ? `${assistantName} Ready`
              : 'Muted'}
          </span>
        </div>
      </div>

      {/* 2. Draggable or Clickable 3D Glass Orb */}
      <div
        onPointerDown={handleOrbPointerDown}
        onPointerMove={handleOrbPointerMove}
        onPointerUp={handleOrbPointerUp}
        onPointerCancel={() => {
          dragStartRef.current = null;
          isDraggingRef.current = false;
        }}
        className="cursor-pointer orb-float-anim relative flex items-center justify-center select-none"
        title={disableDrag ? `Click to talk to ${assistantName}` : `Click to talk • Drag to move`}
      >
        {/* Halo Glow */}
        <div
          className="absolute -inset-2 rounded-full blur-md opacity-40 transition-all duration-700 pointer-events-none"
          style={{ background: `radial-gradient(circle, ${currentColor.hex} 0%, transparent 70%)` }}
        />

        {/* 3D Glass Orb Shell */}
        <div
          className="relative w-28 h-28 rounded-full glass-orb-layer overflow-hidden bg-black flex items-center justify-center transition-transform duration-300 hover:scale-[1.03]"
          style={{
            boxShadow: `0 4px 14px -2px rgba(0, 0, 0, 0.6), 0 0 16px ${currentColor.hex}33, inset 0 2px 4px rgba(255, 255, 255, 0.8), inset 0 12px 24px rgba(255, 255, 255, 0.25), inset 0 -10px 20px rgba(0, 0, 0, 0.8), inset -4px 0 8px rgba(255, 255, 255, 0.15)`,
          }}
        >
          <canvas ref={canvasRef} width={112} height={112} className="w-full h-full block rounded-full pointer-events-none" />

          {/* Specular Curved Reflection */}
          <div
            className="absolute top-1 left-2.5 w-16 h-8 rounded-full blur-[0.8px] transform -rotate-30 pointer-events-none"
            style={{
              background: 'linear-gradient(135deg, rgba(255,255,255,0.92) 0%, rgba(255,255,255,0.32) 28%, transparent 70%)',
            }}
          />

          {/* Secondary Rim Reflection */}
          <div
            className="absolute bottom-1.5 right-2.5 w-8 h-4 rounded-full blur-[1.5px] pointer-events-none"
            style={{ background: 'radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%)' }}
          />

          {/* Border Ring */}
          <div className="absolute inset-0 rounded-full border border-white/20 pointer-events-none" />

          {/* Audio Waveforms for Speaking/Listening */}
          {(orbState === 'speaking' || orbState === 'listening') && (
            <div className="absolute inset-0 flex items-center justify-center gap-1 pointer-events-none">
              <span className="w-1 bg-white/95 rounded-full animate-pulse h-2" />
              <span className="w-1 bg-white/95 rounded-full animate-pulse h-5 delay-75" />
              <span className="w-1 bg-white/95 rounded-full animate-pulse h-7 delay-150" />
              <span className="w-1 bg-white/95 rounded-full animate-pulse h-3.5 delay-100" />
            </div>
          )}

          {/* Executing Spinner Ring */}
          {orbState === 'thinking' && (
            <div className="absolute inset-2 rounded-full border-2 border-transparent border-t-purple-400 border-r-purple-300 animate-spin pointer-events-none" />
          )}

          {orbState === 'executing' && (
            <div className="absolute inset-2 rounded-full border-2 border-transparent border-t-amber-400 border-b-orange-400 animate-spin pointer-events-none" />
          )}

          {/* Ambient Wake Indicator Dot */}
          <div
            className={`absolute bottom-2 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full pointer-events-none transition-colors ${
              isAmbientListening ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]' : 'bg-zinc-600'
            }`}
            title={isAmbientListening ? 'Hands-free wake active' : 'Wake paused'}
          />
        </div>
      </div>

      {/* 3. Floating Micro Controls (Neatly anchored beneath orb) */}
      {!disableDrag && (
        <div
          className={`mt-1.5 flex items-center gap-1 bg-black/90 backdrop-blur-md px-2 py-0.5 rounded-full border border-white/15 shadow-xl transition-all duration-200 z-30 no-drag ${
            isQuickInputOpen ? 'opacity-0 pointer-events-none' : 'opacity-100 translate-y-0 scale-100'
          }`}
        >
          <button
            onClick={(e) => {
              e.stopPropagation();
              onActivate();
            }}
            onPointerDown={(e) => e.stopPropagation()}
            className="w-5 h-5 rounded-full text-zinc-300 hover:text-emerald-400 hover:bg-white/10 flex items-center justify-center transition cursor-pointer"
            title="Click to talk (Ctrl+Space)"
          >
            <Mic className="w-3 h-3" />
          </button>

          {onToggleTextInput && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleTextInput();
              }}
              onPointerDown={(e) => e.stopPropagation()}
              className="w-5 h-5 rounded-full text-zinc-300 hover:text-sky-400 hover:bg-white/10 flex items-center justify-center transition cursor-pointer"
              title="Type a command"
            >
              <MessageSquare className="w-3 h-3" />
            </button>
          )}

          {onToggleMusic && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onToggleMusic();
              }}
              onPointerDown={(e) => e.stopPropagation()}
              className={`w-5 h-5 rounded-full flex items-center justify-center transition cursor-pointer ${
                isMusicActive
                  ? isPlayerTucked
                    ? 'text-emerald-400 hover:text-white hover:bg-white/10'
                    : 'text-black bg-emerald-400 hover:bg-emerald-300'
                  : 'text-zinc-400 hover:text-white hover:bg-white/10'
              }`}
              title={isPlayerTucked ? 'Reveal Music Player (or swipe right)' : 'Tuck Music Player into Orb (or swipe left)'}
            >
              <Music className="w-3 h-3" />
            </button>
          )}

          {onOpenSettings && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onOpenSettings();
              }}
              onPointerDown={(e) => e.stopPropagation()}
              className="w-5 h-5 rounded-full text-zinc-300 hover:text-white hover:bg-white/10 flex items-center justify-center transition cursor-pointer"
              title="Settings & Controls"
            >
              <Settings className="w-3 h-3" />
            </button>
          )}

          {onOpenWindowMode && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onOpenWindowMode();
              }}
              onPointerDown={(e) => e.stopPropagation()}
              className="w-5 h-5 rounded-full text-zinc-300 hover:text-emerald-400 hover:bg-white/10 flex items-center justify-center transition cursor-pointer"
              title="Expand to Full Window Mode"
            >
              <Maximize2 className="w-3 h-3" />
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default FloatingOrb;
