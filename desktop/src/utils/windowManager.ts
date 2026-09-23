export type WidgetViewMode = 'window' | 'orb' | 'compact' | 'expanded' | 'settings' | 'dashboard';

export interface WidgetDimensions {
  width: number;
  height: number;
}

export const WIDGET_DIMENSIONS: Record<WidgetViewMode, WidgetDimensions> = {
  window: { width: 960, height: 700 },
  orb: { width: 260, height: 260 },
  compact: { width: 520, height: 260 },
  expanded: { width: 540, height: 620 },
  settings: { width: 640, height: 520 },
  dashboard: { width: 960, height: 700 },
};

/**
 * Clamps coordinates to the available screen working area.
 */
export function clampWidgetPositionToScreen(x: number, y: number, width: number, height: number): { x: number; y: number } {
  if (typeof window === 'undefined' || !window.screen) return { x, y };
  const availW = window.screen.availWidth || 1920;
  const availH = window.screen.availHeight || 1080;
  const margin = 12;
  const clampedX = Math.max(margin, Math.min(x, availW - width - margin));
  const clampedY = Math.max(margin, Math.min(y, availH - height - margin));
  return { x: clampedX, y: clampedY };
}

/**
 * Resizes the native floating desktop window dynamically.
 * Works seamlessly in Tauri v2 and pywebview environments.
 */
export async function resizeWidget(mode: WidgetViewMode, customDimensions?: WidgetDimensions): Promise<void> {
  const dims = customDimensions || WIDGET_DIMENSIONS[mode];
  const width = Math.round(dims.width);
  const height = Math.round(dims.height);

  // In Tauri, native resize_window handles multi-monitor DPI scaling and work area clamping cleanly


  // 1. Tauri v2 invoke (only if running inside Tauri)
  if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('resize_window', { width, height });
      return;
    } catch (e) {
      console.warn('Tauri resize notice:', e);
    }
  }

  // 2. pywebview JS API (with retry if API is still binding)
  const applyPywebview = async (): Promise<boolean> => {
    try {
      const pywebview = (window as unknown as { pywebview?: { api?: { resize_window?: (w: number, h: number) => Promise<any> } } }).pywebview;
      if (pywebview?.api?.resize_window) {
        const res = await pywebview.api.resize_window(width, height);
        if (res && typeof res.x === 'number' && typeof res.y === 'number') {
          saveWidgetPosition(res.x, res.y);
        }
        return true;
      }
    } catch {}
    return false;
  };

  if (await applyPywebview()) return;

  // Retry after short delays if pywebview bridge is still attaching
  for (const delay of [100, 300, 600]) {
    setTimeout(async () => {
      await applyPywebview();
    }, delay);
  }
}

/**
 * Persists widget position coordinates to localStorage and attempts native positioning.
 */
export async function saveWidgetPosition(x: number, y: number): Promise<void> {
  try {
    localStorage.setItem('daisy_widget_pos_x', String(Math.round(x)));
    localStorage.setItem('daisy_widget_pos_y', String(Math.round(y)));
  } catch {}
}

/**
 * Restores saved widget position on startup.
 */
export async function restoreWidgetPosition(): Promise<void> {
  try {
    const rawX = localStorage.getItem('daisy_widget_pos_x');
    const rawY = localStorage.getItem('daisy_widget_pos_y');
    if (rawX === null || rawY === null) return;

    const x = parseInt(rawX, 10);
    const y = parseInt(rawY, 10);
    if (isNaN(x) || isNaN(y)) return;

    // 1. Tauri v2
    if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('set_window_position', { x, y });
        return;
      } catch {}
    }

    // 2. pywebview
    const applyPos = async (): Promise<boolean> => {
      try {
        const pywebview = (window as unknown as { pywebview?: { api?: { set_window_position?: (x: number, y: number) => Promise<unknown> } } }).pywebview;
        if (pywebview?.api?.set_window_position) {
          await pywebview.api.set_window_position(x, y);
          return true;
        }
      } catch {}
      return false;
    };

    if (await applyPos()) return;
    setTimeout(applyPos, 200);
  } catch {}
}

/**
 * Toggles window always-on-top behavior.
 */
export async function setWidgetOnTop(onTop: boolean): Promise<void> {
  // 1. Tauri v2
  if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('set_always_on_top', { alwaysOnTop: onTop });
      return;
    } catch {}
  }

  // 2. pywebview
  const applyOnTop = async (): Promise<boolean> => {
    try {
      const pywebview = (window as unknown as { pywebview?: { api?: { set_on_top?: (onTop: boolean) => Promise<unknown> } } }).pywebview;
      if (pywebview?.api?.set_on_top) {
        await pywebview.api.set_on_top(onTop);
        return true;
      }
    } catch {}
    return false;
  };

  if (await applyOnTop()) return;
  setTimeout(applyOnTop, 200);
}

/**
 * Minimizes the native window.
 */
export async function minimizeWindow(): Promise<void> {
  // 1. Tauri v2
  if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('minimize_window');
      return;
    } catch {}
  }

  // 2. pywebview
  try {
    const pywebview = (window as unknown as { pywebview?: { api?: { minimize_window?: () => Promise<unknown> } } }).pywebview;
    if (pywebview?.api?.minimize_window) {
      await pywebview.api.minimize_window();
    }
  } catch {}
}

/**
 * Closes / terminates the native application window.
 */
export async function closeWindow(): Promise<void> {
  // Fire shutdown beacon to stop Spotify immediately
  try {
    if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
      navigator.sendBeacon('http://127.0.0.1:8000/system/shutdown');
    } else {
      fetch('http://127.0.0.1:8000/system/shutdown', { method: 'POST', keepalive: true }).catch(() => {});
    }
  } catch {}

  // 1. Tauri v2
  if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('close_window');
      return;
    } catch {}
  }

  // 2. pywebview
  try {
    const pywebview = (window as unknown as { pywebview?: { api?: { close_window?: () => Promise<unknown> } } }).pywebview;
    if (pywebview?.api?.close_window) {
      await pywebview.api.close_window();
    }
  } catch {}
}

/**
 * Cleanly terminates Daisy window and background server.
 */
export async function closeApp(): Promise<void> {
  // 1. Immediately request backend shutdown to stop Spotify and TTS
  try {
    if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
      navigator.sendBeacon('http://127.0.0.1:8000/system/shutdown');
    } else {
      fetch('http://127.0.0.1:8000/system/shutdown', { method: 'POST', keepalive: true }).catch(() => {});
    }
  } catch {}

  // 2. pywebview JS API
  try {
    const pywebview = (window as unknown as { pywebview?: { api?: { close_app?: () => Promise<unknown> } } }).pywebview;
    if (pywebview?.api?.close_app) {
      await pywebview.api.close_app();
      return;
    }
  } catch {}

  // 3. Tauri v2
  if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('exit_app');
      return;
    } catch {}
  }

  // 4. Fallback close window
  await closeWindow();
}

/**
 * Switches native window between Full Window mode ('window') and Floating Widget mode ('floating').
 */
export async function setNativeWindowMode(mode: 'window' | 'floating'): Promise<void> {
  // 1. Tauri v2
  if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
    try {
      const { invoke } = await import('@tauri-apps/api/core');
      await invoke('set_window_mode', { mode });
    } catch {}
  }

  // 2. pywebview JS API with retry
  const applyMode = async (): Promise<boolean> => {
    try {
      const pywebview = (window as unknown as { pywebview?: { api?: { set_window_mode?: (m: string) => Promise<unknown> } } }).pywebview;
      if (pywebview?.api?.set_window_mode) {
        await pywebview.api.set_window_mode(mode);
        return true;
      }
    } catch {}
    return false;
  };

  if (await applyMode()) return;
  for (const delay of [150, 350, 700]) {
    setTimeout(applyMode, delay);
  }
}

/**
 * Initiates native OS window dragging (works seamlessly in Tauri v2 and pywebview).
 */
export async function startDragWindow(): Promise<void> {
  // 1. Tauri v2
  if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
    try {
      const { getCurrentWebviewWindow } = await import('@tauri-apps/api/webviewWindow');
      await getCurrentWebviewWindow().startDragging();
      return;
    } catch {}
  }

  // 2. pywebview
  try {
    const pywebview = (window as unknown as { pywebview?: { api?: { drag_window?: () => Promise<unknown> } } }).pywebview;
    if (pywebview?.api?.drag_window) {
      await pywebview.api.drag_window();
    }
  } catch {}
}

/**
 * Smoothly offsets window position by delta pixels (high-frequency fallback).
 */
export async function moveWindowBy(dx: number, dy: number): Promise<void> {
  // 1. pywebview
  try {
    const pywebview = (window as unknown as { pywebview?: { api?: { move_window_by?: (dx: number, dy: number) => Promise<unknown> } } }).pywebview;
    if (pywebview?.api?.move_window_by) {
      await pywebview.api.move_window_by(dx, dy);
      return;
    }
  } catch {}
}


