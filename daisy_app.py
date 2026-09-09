import os
import sys

# Ensure WebView2 initializes with transparent default background
os.environ["WEBVIEW2_DEFAULT_BACKGROUND_COLOR"] = "0"

# Ensure UTF-8 output encoding on Windows consoles to prevent UnicodeEncodeError
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import socket
import subprocess
import threading
import time
import urllib.request
import uvicorn
import webview

# Prevent ObjectDisposedException traceback upon native window close
try:
    import logging
    class PywebviewDisposeFilter(logging.Filter):
        def filter(self, record):
            # Suppress ObjectDisposedException traceback when WebView2 is closing/disposed
            if record.exc_info and "ObjectDisposedException" in str(record.exc_info[1]):
                return False
            msg = record.getMessage()
            if "ObjectDisposedException" in msg or "disposed object" in msg.lower():
                return False
            return True

    logging.getLogger("pywebview").addFilter(PywebviewDisposeFilter())

    from webview.platforms import edgechromium
    import json
    from threading import Semaphore
    from System import Action, Func, Object, String, Type
    from System.Threading.Tasks import Task

    def _safe_evaluate_js(self, script: str, parse_json: bool = True):
        wv = getattr(self, 'webview', None)
        if wv is None:
            return None
        try:
            if getattr(wv, 'IsDisposed', False) or getattr(wv, 'Disposing', False):
                return None
            if hasattr(wv, 'IsHandleCreated') and not wv.IsHandleCreated:
                return None
        except Exception:
            return None

        def _callback(res):
            nonlocal result
            if parse_json and res is not None:
                try:
                    result = json.loads(res)
                except Exception:
                    result = res
            else:
                result = res
            try:
                semaphore.release()
            except Exception:
                pass

        result = None
        semaphore = Semaphore(0)

        try:
            wv.Invoke(
                Func[Object](
                    lambda: wv.ExecuteScriptAsync(script).ContinueWith(
                        Action[Task[String]](lambda task: _callback(json.loads(task.Result))),
                        self.syncContextTaskScheduler,
                    )
                )
            )
            semaphore.acquire()
        except Exception as e:
            err_str = str(e)
            if "ObjectDisposedException" not in err_str and "disposed" not in err_str.lower():
                logging.getLogger('pywebview').warning(f"Script evaluation note: {e}")
            try:
                semaphore.release()
            except Exception:
                pass

        return result

    edgechromium.EdgeChrome.evaluate_js = _safe_evaluate_js
except Exception:
    pass

import ctypes
from ctypes import wintypes

class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", wintypes.INT),
        ("cxRightWidth", wintypes.INT),
        ("cyTopHeight", wintypes.INT),
        ("cyBottomHeight", wintypes.INT),
    ]

def enable_dwm_transparency(hwnd):
    try:
        dwm = ctypes.windll.dwmapi
        margins = MARGINS(-1, -1, -1, -1)
        dwm.DwmExtendFrameIntoClientArea(wintypes.HWND(hwnd), ctypes.byref(margins))
    except Exception as e:
        print(f"[Daisy] DWM transparency note: {e}")

# Pre-load Windows Forms and System.Drawing assemblies
try:
    import clr
    clr.AddReference('System.Windows.Forms')
    clr.AddReference('System.Drawing')
except Exception:
    pass

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.main import app as fastapi_app

def is_port_in_use(port: int = 8000) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def cleanup_zombie_port(port: int = 8000):
    """Detects and terminates hung zombie processes holding the port."""
    try:
        out = subprocess.check_output(
            f'netstat -ano | findstr :{port}', shell=True, text=True, stderr=subprocess.DEVNULL
        )
        my_pid = os.getpid()
        for line in out.strip().splitlines():
            parts = line.strip().split()
            if len(parts) >= 5 and f":{port}" in parts[1]:
                state = parts[3].upper()
                pid = int(parts[4])
                if pid != my_pid and pid > 0:
                    print(f"[Daisy] Clearing stale process {pid} holding port {port} ({state})...")
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                    time.sleep(0.5)
    except Exception:
        pass

def wait_for_backend(url: str = "http://127.0.0.1:8000/", timeout: float = 4.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.15)
    return False

def start_backend():
    """Runs FastAPI backend on http://127.0.0.1:8000 in background thread."""
    config = uvicorn.Config(
        fastapi_app,
        host="127.0.0.1",
        port=8000,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(config)
    server.run()

class DesktopApi:
    """
    Thread-safe JS-to-Python Bridge for pywebview.
    Directly invokes Windows Forms methods on the STA UI thread to prevent
    64-bit handle overflow and avoid DWM / accessibility recursion deadlocks.
    """
    def __init__(self):
        self._window = None

    def _get_window(self):
        return self._window or (webview.windows[0] if getattr(webview, 'windows', None) else None)

    def _get_native_form(self):
        win = self._get_window()
        return getattr(win, 'native', None) if win else None

    def resize_window(self, width: int, height: int):
        form = self._get_native_form()
        if form:
            try:
                import System.Drawing as Drawing
                import System.Windows.Forms as WinForms
                target_w = max(180, int(width))
                target_h = max(180, int(height))

                def _apply():
                    scale = getattr(form, '_scale', 1.0)
                    if hasattr(form, 'DeviceDpi') and form.DeviceDpi > 0:
                        scale = form.DeviceDpi / 96.0
                    phys_w = int(round(target_w * scale))
                    phys_h = int(round(target_h * scale))

                    # Smart Positioning: automatically adjust position if expanding near screen boundaries
                    try:
                        screen = WinForms.Screen.FromControl(form)
                        working_area = screen.WorkingArea
                        margin = int(round(16 * scale))

                        curr_x = form.Location.X
                        curr_y = form.Location.Y
                        new_x = curr_x
                        new_y = curr_y

                        if new_x + phys_w > working_area.Right - margin:
                            new_x = working_area.Right - phys_w - margin
                        if new_x < working_area.Left + margin:
                            new_x = working_area.Left + margin

                        if new_y + phys_h > working_area.Bottom - margin:
                            new_y = working_area.Bottom - phys_h - margin
                        if new_y < working_area.Top + margin:
                            new_y = working_area.Top + margin

                        if new_x != curr_x or new_y != curr_y:
                            form.Location = Drawing.Point(new_x, new_y)
                    except Exception:
                        pass

                    form.Size = Drawing.Size(phys_w, phys_h)

                if form.InvokeRequired:
                    form.BeginInvoke(WinForms.MethodInvoker(_apply))
                else:
                    _apply()
                return {"status": "ok", "width": target_w, "height": target_h}
            except Exception as e:
                return {"error": str(e)}

        # Fallback to pywebview API
        win = self._get_window()
        if win:
            try:
                win.resize(int(width), int(height))
                return {"status": "ok"}
            except Exception as e:
                return {"error": str(e)}
        return {"error": "no window"}

    def get_window_position(self):
        form = self._get_native_form()
        if form:
            try:
                scale = getattr(form, '_scale', 1.0)
                if hasattr(form, 'DeviceDpi') and form.DeviceDpi > 0:
                    scale = form.DeviceDpi / 96.0
                loc = form.Location
                return {"x": int(loc.X / scale), "y": int(loc.Y / scale)}
            except Exception:
                pass
        return {"x": 0, "y": 0}

    def set_window_position(self, x: int, y: int):
        form = self._get_native_form()
        if form:
            try:
                import System.Drawing as Drawing
                import System.Windows.Forms as WinForms
                target_x = int(x)
                target_y = int(y)

                def _apply():
                    scale = getattr(form, '_scale', 1.0)
                    if hasattr(form, 'DeviceDpi') and form.DeviceDpi > 0:
                        scale = form.DeviceDpi / 96.0
                    phys_x = int(round(target_x * scale))
                    phys_y = int(round(target_y * scale))

                    # Smart Positioning: ensure position is clamped within screen working area
                    try:
                        screen = WinForms.Screen.FromPoint(Drawing.Point(phys_x, phys_y))
                        working_area = screen.WorkingArea
                        margin = int(round(16 * scale))
                        phys_w = form.Size.Width
                        phys_h = form.Size.Height

                        if phys_x + phys_w > working_area.Right - margin:
                            phys_x = working_area.Right - phys_w - margin
                        if phys_x < working_area.Left + margin:
                            phys_x = working_area.Left + margin

                        if phys_y + phys_h > working_area.Bottom - margin:
                            phys_y = working_area.Bottom - phys_h - margin
                        if phys_y < working_area.Top + margin:
                            phys_y = working_area.Top + margin
                    except Exception:
                        pass

                    form.Location = Drawing.Point(phys_x, phys_y)

                if form.InvokeRequired:
                    form.BeginInvoke(WinForms.MethodInvoker(_apply))
                else:
                    _apply()
                return {"status": "ok", "x": target_x, "y": target_y}
            except Exception as e:
                return {"error": str(e)}

        win = self._get_window()
        if win:
            try:
                win.move(int(x), int(y))
                return {"status": "ok"}
            except Exception as e:
                return {"error": str(e)}
        return {"error": "no window"}

    def set_on_top(self, on_top: bool):
        form = self._get_native_form()
        if form:
            try:
                import System.Windows.Forms as WinForms
                val = bool(on_top)

                def _apply():
                    form.TopMost = val

                if form.InvokeRequired:
                    form.BeginInvoke(WinForms.MethodInvoker(_apply))
                else:
                    _apply()
                return {"status": "ok"}
            except Exception as e:
                return {"error": str(e)}

        win = self._get_window()
        if win:
            try:
                win.on_top = bool(on_top)
                return {"status": "ok"}
            except Exception as e:
                return {"error": str(e)}
        return {"error": "no window"}

    def minimize_window(self):
        form = self._get_native_form()
        if form:
            try:
                import System.Windows.Forms as WinForms

                def _apply():
                    form.WindowState = WinForms.FormWindowState.Minimized

                if form.InvokeRequired:
                    form.BeginInvoke(WinForms.MethodInvoker(_apply))
                else:
                    _apply()
                return {"status": "ok"}
            except Exception as e:
                return {"error": str(e)}

        win = self._get_window()
        if win:
            try:
                win.minimize()
                return {"status": "ok"}
            except Exception as e:
                return {"error": str(e)}
        return {"error": "no window"}

    def close_window(self):
        form = self._get_native_form()
        if form:
            try:
                import System.Windows.Forms as WinForms

                def _apply():
                    form.Close()

                if form.InvokeRequired:
                    form.BeginInvoke(WinForms.MethodInvoker(_apply))
                else:
                    _apply()
                return {"status": "ok"}
            except Exception as e:
                return {"error": str(e)}

        win = self._get_window()
        if win:
            try:
                win.destroy()
                return {"status": "ok"}
            except Exception as e:
                return {"error": str(e)}
        return {"error": "no window"}

    def close_app(self):
        """Cleanly shuts down Daisy desktop window and background process."""
        try:
            self.close_window()
        except Exception:
            pass
        import threading
        threading.Thread(target=lambda: (time.sleep(0.4), os._exit(0)), daemon=True).start()
        return {"status": "closing"}

    def set_window_mode(self, mode: str):
        """
        Switches between 'window' (full application window) and 'floating' (desktop overlay widget).
        In 'window' mode: normal z-order, solid dark window background.
        In 'floating' mode: always-on-top, transparent desktop cutout key.
        """
        form = self._get_native_form()
        if not form:
            return {"error": "no form"}
        try:
            import System.Windows.Forms as WinForms
            import System.Drawing as Drawing

            def _apply():
                try:
                    if mode == 'floating':
                        form.TopMost = True
                        form.AllowTransparency = True
                        key = Drawing.Color.FromArgb(1, 1, 1)
                        form.BackColor = key
                        form.TransparencyKey = key
                        enable_dwm_transparency(int(form.Handle.ToInt64()))
                    else:
                        form.TopMost = False
                        form.TransparencyKey = Drawing.Color.Empty
                        form.BackColor = Drawing.Color.FromArgb(9, 11, 17)
                except Exception as e:
                    print(f"[DaisyApi] Error setting window mode: {e}")

            if form.InvokeRequired:
                form.BeginInvoke(WinForms.MethodInvoker(_apply))
            else:
                _apply()
            return {"status": "ok", "mode": mode}
        except Exception as e:
            return {"error": str(e)}


def main():
    # 1. Start backend thread (with zombie port recovery)
    if is_port_in_use(8000):
        print("[Daisy] Port 8000 detected. Testing backend responsiveness...")
        if wait_for_backend("http://127.0.0.1:8000/", timeout=1.5):
            print("[Daisy] Connected to running Daisy backend on port 8000.")
        else:
            print("[Daisy] Port 8000 is unresponsive (zombie process). Cleaning up...")
            cleanup_zombie_port(8000)
            time.sleep(0.5)
            print("[Daisy] Starting fresh Daisy FastAPI backend on http://127.0.0.1:8000...")
            backend_thread = threading.Thread(target=start_backend, daemon=True)
            backend_thread.start()
            wait_for_backend("http://127.0.0.1:8000/", timeout=5.0)
    else:
        print("[Daisy] Starting Daisy FastAPI backend thread on http://127.0.0.1:8000...")
        backend_thread = threading.Thread(target=start_backend, daemon=True)
        backend_thread.start()
        wait_for_backend("http://127.0.0.1:8000/", timeout=5.0)

    # 2. Determine frontend target
    dist_dir = os.path.join(PROJECT_ROOT, "desktop", "dist")
    if os.path.exists(dist_dir):
        url = "http://127.0.0.1:8000/app"
    else:
        url = "http://localhost:5173"

    print(f"[Daisy] Launching Daisy Desktop Native Window ({url})...")

    # 3. Create native desktop window using Windows Edge WebView2
    api = DesktopApi()
    window = webview.create_window(
        title="Daisy 🌼",
        url=url,
        width=940,
        height=680,
        resizable=True,
        frameless=True,
        easy_drag=True,
        on_top=False,
        transparent=True,
        js_api=api
    )
    api._window = window

    def on_window_shown():
        try:
            form = getattr(window, 'native', None)
            if form:
                import System.Windows.Forms as WinForms
                import System.Drawing as Drawing
                def _setup():
                    try:
                        form.AllowTransparency = True
                        form.BackColor = Drawing.Color.FromArgb(9, 11, 17)
                    except Exception as e:
                        print(f"[Daisy] Setup Transparency note: {e}")
                if form.InvokeRequired:
                    form.BeginInvoke(WinForms.MethodInvoker(_setup))
                else:
                    _setup()
        except Exception as err:
            print(f"[Daisy] Shown hook note: {err}")

    window.events.shown += on_window_shown

    def on_window_closed():
        threading.Thread(target=lambda: (time.sleep(0.1), os._exit(0)), daemon=True).start()

    window.events.closed += on_window_closed

    # 4. Start GUI event loop
    try:
        webview.start(debug=False)
    finally:
        os._exit(0)

if __name__ == "__main__":
    main()
