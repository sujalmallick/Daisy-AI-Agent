import os
import sys
import socket
import threading
import time
import urllib.request
import uvicorn
import webview

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.main import app as fastapi_app

def is_port_in_use(port: int = 8000) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def wait_for_backend(url: str = "http://127.0.0.1:8000/", timeout: float = 5.0) -> bool:
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
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")

def main():
    # 1. Start backend thread if not already running
    if is_port_in_use(8000):
        print("⚡ Port 8000 in use. Checking if Daisy backend is already active...")
        if wait_for_backend("http://127.0.0.1:8000/", timeout=1.0):
            print(" Connected to running Daisy backend on port 8000.")
        else:
            print("⚠️ Port 8000 is occupied by another process. Will attempt to proceed.")
    else:
        print("🚀 Starting Daisy FastAPI backend thread on http://127.0.0.1:8000...")
        backend_thread = threading.Thread(target=start_backend, daemon=True)
        backend_thread.start()
        wait_for_backend("http://127.0.0.1:8000/", timeout=5.0)

    # 2. Determine frontend target
    dist_dir = os.path.join(PROJECT_ROOT, "desktop", "dist")
    if os.path.exists(dist_dir):
        url = "http://127.0.0.1:8000/app"
    else:
        url = "http://localhost:5173"

    print(f"🌼 Launching Daisy Desktop Native Window ({url})...")

    # 3. Create native desktop window using Windows Edge WebView2
    window = webview.create_window(
        title="Daisy 🌼",
        url=url,
        width=380,
        height=660,
        resizable=True,
        frameless=False,
        easy_drag=True,
        on_top=True,
        background_color="#07090e"
    )

    # 4. Start GUI event loop
    webview.start(debug=False)

if __name__ == "__main__":
    main()

