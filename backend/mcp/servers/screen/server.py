import os
import io
import time
import base64
import ctypes
from ctypes import wintypes
import logging
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image

logger = logging.getLogger("daisy.mcp.screen")

# Pre-define cache directories
CACHE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".daisy_cache", "screenshots"))
os.makedirs(CACHE_DIR, exist_ok=True)


class ScreenMCPServer:
    """
    Screen Vision & Visual Guidance MCP Server.
    Provides Daisy with HeyClicky-style on-screen awareness:
      - DPI-aware, high-performance Win32 GDI screen capture (<40ms)
      - Active foreground window inspection
      - Visual guidance coordinate helpers
    """

    def __init__(self):
        self._last_capture_time = 0
        self._last_capture_data = None

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "capture_screen",
                "description": "Takes a screenshot of the user's current desktop screen to see open windows, code, errors, documents, or UI elements.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_dimension": {
                            "type": "integer",
                            "description": "Max width/height for image scaling (default 1280)."
                        }
                    }
                }
            },
            {
                "name": "get_active_window",
                "description": "Retrieves the window title and bounds of the user's currently focused foreground application.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "highlight_element",
                "description": "Triggers an on-screen visual pointer or bounding box to guide the user's eyes to a specific button, menu item, or region on their screen.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "x": {
                            "type": "integer",
                            "description": "X coordinate in screen pixels (or normalized 0-1000)."
                        },
                        "y": {
                            "type": "integer",
                            "description": "Y coordinate in screen pixels (or normalized 0-1000)."
                        },
                        "width": {
                            "type": "integer",
                            "description": "Width of the highlight area (default 60)."
                        },
                        "height": {
                            "type": "integer",
                            "description": "Height of the highlight area (default 60)."
                        },
                        "label": {
                            "type": "string",
                            "description": "Optional text label to display near the pointer (e.g. 'Click here', 'Submit Button')."
                        }
                    },
                    "required": ["x", "y"]
                }
            }
        ]

    def _get_foreground_window_title(self) -> str:
        """Returns the title of the user's foreground application window."""
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if not hwnd:
                return "Desktop"
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                return buf.value
        except Exception as e:
            logger.debug(f"Could not read foreground window: {e}")
        return "Active Window"

    def take_screenshot(self, max_dim: int = 1280) -> Tuple[Optional[Image.Image], str, str, int, int]:
        """
        High-performance Win32 GDI screen capture.
        Returns: (pil_image, local_file_path, base64_data_url, width, height)
        """
        try:
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            
            # Make process DPI aware for true pixel bounds
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass

            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            if w <= 0 or h <= 0:
                w, h = 1920, 1080

            hdc_screen = user32.GetDC(0)
            hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
            gdi32.SelectObject(hdc_mem, hbmp)
            
            # 0x00CC0020 = SRCCOPY
            gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, 0, 0, 0x00CC0020)
            
            bmpinfo = (ctypes.c_byte * 40)()
            ctypes.cast(bmpinfo, ctypes.POINTER(ctypes.c_int32))[0] = 40
            ctypes.cast(bmpinfo, ctypes.POINTER(ctypes.c_int32))[1] = w
            ctypes.cast(bmpinfo, ctypes.POINTER(ctypes.c_int32))[2] = -h
            ctypes.cast(bmpinfo, ctypes.POINTER(ctypes.c_int16))[6] = 1
            ctypes.cast(bmpinfo, ctypes.POINTER(ctypes.c_int16))[7] = 32
            
            buf = (ctypes.c_byte * (w * h * 4))()
            gdi32.GetDIBits(hdc_mem, hbmp, 0, h, ctypes.byref(buf), ctypes.byref(bmpinfo), 0)
            
            gdi32.DeleteObject(hbmp)
            gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc_screen)
            
            im = Image.frombuffer("RGBA", (w, h), bytes(buf), "raw", "BGRA", 0, 1).convert("RGB")
            
            # Save latest high-res JPEG
            file_path = os.path.join(CACHE_DIR, "latest.jpg")
            im.save(file_path, "JPEG", quality=85)
            
            # Create downscaled preview/thumbnail for fast transmission to LLM & UI
            im_thumb = im.copy()
            im_thumb.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            bio = io.BytesIO()
            im_thumb.save(bio, format="JPEG", quality=75)
            b64 = base64.b64encode(bio.getvalue()).decode("utf-8")
            data_url = f"data:image/jpeg;base64,{b64}"
            
            return im_thumb, file_path, data_url, w, h
        except Exception as e:
            logger.error(f"Win32 screen capture failed: {e}", exc_info=True)
            return None, "", "", 0, 0

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        arguments = arguments or {}

        if tool_name == "capture_screen":
            max_dim = int(arguments.get("max_dimension", 1280))
            _, file_path, data_url, w, h = self.take_screenshot(max_dim=max_dim)
            active_win = self._get_foreground_window_title()
            
            if not file_path:
                return {"error": "Failed to capture desktop screen."}

            return {
                "status": "captured",
                "width": w,
                "height": h,
                "active_window": active_win,
                "path": file_path,
                "preview_data_url": data_url,
                "card_type": "vision",
                "card_data": {
                    "width": w,
                    "height": h,
                    "active_window": active_win,
                    "preview_url": data_url,
                    "timestamp": time.strftime("%H:%M:%S")
                },
                "message": f"Captured {w}x{h} screen (Active window: {active_win})."
            }

        elif tool_name == "get_active_window":
            title = self._get_foreground_window_title()
            return {
                "active_window": title,
                "status": "ok"
            }

        elif tool_name == "highlight_element":
            x = int(arguments.get("x", 0))
            y = int(arguments.get("y", 0))
            w = int(arguments.get("width", 60))
            h = int(arguments.get("height", 60))
            label = str(arguments.get("label", "Target"))

            return {
                "status": "highlighted",
                "x": x,
                "y": y,
                "width": w,
                "height": h,
                "label": label,
                "card_type": "vision",
                "card_data": {
                    "pointer_target": {"x": x, "y": y},
                    "highlight_box": {"x": x, "y": y, "width": w, "height": h},
                    "label": label
                },
                "message": f"Pointing to {label} at ({x}, {y})."
            }

        return {"error": f"Unknown Screen tool: '{tool_name}'"}


# Instantiate and auto-register with mcp_manager
from backend.mcp.manager import mcp_manager
screen_server = ScreenMCPServer()
mcp_manager.register_server("screen", screen_server)
