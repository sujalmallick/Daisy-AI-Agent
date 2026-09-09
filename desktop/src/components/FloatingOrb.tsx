import React, { useEffect, useRef } from 'react';

export type OrbStateType = 'idle' | 'listening' | 'thinking' | 'executing' | 'speaking' | 'error';
export type ThemeType = 'glassmorphism' | 'sleek' | 'cyberpunk' | 'aurora';

interface FloatingOrbProps {
  orbState: OrbStateType;
  theme: ThemeType;
  onSingleClick: () => void;
  onDoubleClick: () => void;
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
  onSingleClick,
  onDoubleClick,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const clickTimerRef = useRef<number | null>(null);

  const getColor = () => {
    if (orbState === 'idle') {
      const idleMap = STATE_COLORS.idle as Record<string, { r: number; g: number; b: number; hex: string }>;
      return idleMap[theme] || idleMap.glassmorphism;
    }
    const stateObj = STATE_COLORS[orbState] as { all: { r: number; g: number; b: number; hex: string } };
    return stateObj.all;
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animTime = 0;
    let animFrameId: number;

    const render = () => {
      const col = getColor();
      animTime += 0.022;

      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const cx = w / 2;
      const cy = h / 2;

      const grad = ctx.createRadialGradient(
        cx + Math.sin(animTime) * 12,
        cy + Math.cos(animTime * 0.9) * 12,
        4,
        cx,
        cy,
        70
      );

      grad.addColorStop(0, 'rgba(255, 255, 255, 0.98)');
      grad.addColorStop(0.3, `rgba(${col.r}, ${col.g}, ${col.b}, 0.9)`);
      grad.addColorStop(0.72, `rgba(${Math.max(col.r - 40, 5)}, ${Math.max(col.g - 40, 5)}, ${Math.max(col.b - 40, 5)}, 0.92)`);
      grad.addColorStop(1, '#040508');

      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(cx, cy, 70, 0, Math.PI * 2);
      ctx.fill();

      for (let i = 0; i < 3; i++) {
        ctx.beginPath();
        const angle = animTime * 0.9 + (i * Math.PI * 2) / 3;
        const dist = 24 + Math.sin(animTime * 1.6 + i) * 10;
        const bx = cx + Math.cos(angle) * dist;
        const by = cy + Math.sin(angle) * dist;

        const bGrad = ctx.createRadialGradient(bx, by, 2, bx, by, 34);
        bGrad.addColorStop(0, 'rgba(255, 255, 255, 0.5)');
        bGrad.addColorStop(0.5, `rgba(${col.r}, ${col.g}, ${col.b}, 0.3)`);
        bGrad.addColorStop(1, 'transparent');

        ctx.fillStyle = bGrad;
        ctx.arc(bx, by, 34, 0, Math.PI * 2);
        ctx.fill();
      }

      animFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animFrameId);
    };
  }, [orbState, theme]);

  // Debounced click handler to separate single-click (voice) from double-click (expand)
  const handleClick = () => {
    if (clickTimerRef.current !== null) {
      window.clearTimeout(clickTimerRef.current);
      clickTimerRef.current = null;
      onDoubleClick();
    } else {
      clickTimerRef.current = window.setTimeout(() => {
        clickTimerRef.current = null;
        onSingleClick();
      }, 250);
    }
  };

  const currentColor = getColor();

  return (
    <div className="flex flex-col items-center select-none">
      <div
        onClick={handleClick}
        className="orb-float-anim cursor-pointer relative group flex items-center justify-center"
        title="Single click to Speak | Double click for Now Playing"
      >
        {/* Ambient Halo Glow */}
        <div
          className="absolute -inset-10 rounded-full blur-3xl opacity-60 transition-all duration-700 pointer-events-none"
          style={{ background: `radial-gradient(circle, ${currentColor.hex} 0%, transparent 70%)` }}
        />

        {/* Glass Orb Shell */}
        <div
          className="relative w-36 h-36 rounded-full glass-orb-layer overflow-hidden bg-black flex items-center justify-center"
          style={{
            boxShadow: `0 20px 50px -10px rgba(0, 0, 0, 0.95), 0 0 45px ${currentColor.hex}66, inset 0 2px 4px rgba(255, 255, 255, 0.8), inset 0 14px 28px rgba(255, 255, 255, 0.25), inset 0 -12px 24px rgba(0, 0, 0, 0.8), inset -4px 0 10px rgba(255, 255, 255, 0.15)`,
          }}
        >
          <canvas ref={canvasRef} width={144} height={144} className="w-full h-full block rounded-full" />

          {/* Specular Curved Shine */}
          <div
            className="absolute top-1.5 left-3.5 w-24 h-12 rounded-full blur-[1px] transform -rotate-30 pointer-events-none"
            style={{
              background: 'linear-gradient(135deg, rgba(255,255,255,0.92) 0%, rgba(255,255,255,0.35) 28%, transparent 70%)',
            }}
          />

          {/* Secondary Bottom Reflection */}
          <div
            className="absolute bottom-2 right-4 w-12 h-6 rounded-full blur-[2px] pointer-events-none"
            style={{ background: 'radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%)' }}
          />

          {/* Border Ring */}
          <div className="absolute inset-0 rounded-full border border-white/20 pointer-events-none" />

          {/* Audio Waveforms for Speaking/Listening */}
          {(orbState === 'speaking' || orbState === 'listening') && (
            <div className="absolute inset-0 flex items-center justify-center gap-1 pointer-events-none">
              <span className="w-1 bg-white/90 rounded-full animate-pulse h-3" />
              <span className="w-1 bg-white/90 rounded-full animate-pulse h-7 delay-75" />
              <span className="w-1 bg-white/90 rounded-full animate-pulse h-9 delay-150" />
              <span className="w-1 bg-white/90 rounded-full animate-pulse h-5 delay-100" />
            </div>
          )}
        </div>
      </div>

      {/* Breathing Ground Drop Shadow */}
      <div className="w-28 h-4 mt-7 rounded-full bg-black/80 blur-md shadow-breath-anim pointer-events-none" />

      {/* Helper text */}
      <div className="mt-4 text-xs text-zinc-400 font-normal flex items-center gap-2">
        <span>Click to talk •</span>
        <button
          onClick={onDoubleClick}
          className="text-emerald-400 hover:text-emerald-300 font-medium underline underline-offset-4 cursor-pointer"
        >
          Double-click for Now Playing
        </button>
      </div>
    </div>
  );
};
