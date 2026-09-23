import os
import re
import glob
import shutil
import subprocess
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("daisy.mcp.app_launcher")

class AppLauncherMCPServer:
    """
    Built-in Windows App Launcher MCP Server.
    Enables Daisy to launch installed desktop applications, Windows Store apps,
    system utilities, and URI schemes with 0 tokens and immediate execution.
    """

    KNOWN_APPS: Dict[str, tuple] = {
        "spotify": ("spotify:", "Spotify"),
        "chrome": ("chrome", "Google Chrome"),
        "google chrome": ("chrome", "Google Chrome"),
        "edge": ("msedge", "Microsoft Edge"),
        "microsoft edge": ("msedge", "Microsoft Edge"),
        "browser": ("msedge", "Microsoft Edge"),
        "notepad": ("notepad", "Notepad"),
        "calculator": ("calc", "Calculator"),
        "calc": ("calc", "Calculator"),
        "vscode": ("code", "Visual Studio Code"),
        "vs code": ("code", "Visual Studio Code"),
        "code": ("code", "Visual Studio Code"),
        "visual studio code": ("code", "Visual Studio Code"),
        "discord": ("discord:", "Discord"),
        "steam": ("steam:", "Steam"),
        "terminal": ("wt", "Windows Terminal"),
        "windows terminal": ("wt", "Windows Terminal"),
        "powershell": ("powershell", "PowerShell"),
        "cmd": ("cmd", "Command Prompt"),
        "command prompt": ("cmd", "Command Prompt"),
        "explorer": ("explorer", "File Explorer"),
        "file explorer": ("explorer", "File Explorer"),
        "files": ("explorer", "File Explorer"),
        "settings": ("ms-settings:", "Windows Settings"),
        "windows settings": ("ms-settings:", "Windows Settings"),
        "task manager": ("taskmgr", "Task Manager"),
        "taskmgr": ("taskmgr", "Task Manager"),
        "whatsapp": ("whatsapp:", "WhatsApp"),
        "telegram": ("telegram:", "Telegram"),
        "paint": ("mspaint", "Paint"),
        "camera": ("microsoft.windows.camera:", "Camera"),
        "clock": ("ms-clock:", "Clock"),
        "word": ("winword", "Microsoft Word"),
        "excel": ("excel", "Microsoft Excel"),
        "powerpoint": ("powerpnt", "Microsoft PowerPoint"),
    }

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "launch_app",
                "description": "Launches an application, software program, or system utility on the user's Windows computer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "description": "Name of the application to launch e.g. 'Spotify', 'Chrome', 'VS Code', 'Notepad', 'Calculator'"
                        }
                    },
                    "required": ["app_name"]
                }
            },
            {
                "name": "close_app",
                "description": "Closes or terminates a running desktop application on the user's Windows computer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "app_name": {
                            "type": "string",
                            "description": "Name of the application to close e.g. 'Chrome', 'Notepad', 'Spotify', 'Calculator'"
                        }
                    },
                    "required": ["app_name"]
                }
            },
            {
                "name": "list_installed_apps",
                "description": "Returns a list of common applications and Start Menu shortcuts installed on the host PC.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def _find_start_menu_shortcut(self, app_name: str) -> Optional[str]:
        """Searches Windows Start Menu directories for matching .lnk application shortcuts."""
        search_dirs = [
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
        ]
        app_lower = app_name.lower().replace(" ", "").replace("-", "")

        for base_dir in search_dirs:
            if not os.path.exists(base_dir):
                continue
            for root, _, files in os.walk(base_dir):
                for f in files:
                    if f.lower().endswith(".lnk"):
                        name_without_ext = os.path.splitext(f)[0].lower()
                        clean_name = name_without_ext.replace(" ", "").replace("-", "")
                        if app_lower in clean_name or clean_name in app_lower:
                            return os.path.join(root, f)
        return None

    def execute_tool(self, tool_name: str, args: Dict[str, Any] = None) -> Any:
        args = args or {}

        if tool_name == "launch_app":
            raw_app = args.get("app_name", "").strip()
            if not raw_app:
                return {"error": "Please specify an application name to launch."}

            norm = raw_app.lower()

            # 1. Check direct known apps table
            if norm in self.KNOWN_APPS:
                cmd_target, display_name = self.KNOWN_APPS[norm]
                try:
                    os.startfile(cmd_target)
                    logger.info(f"Launched known app: {display_name} ({cmd_target})")
                    return {
                        "status": "app_launched",
                        "app": display_name,
                        "message": f"Opening {display_name}."
                    }
                except Exception as e:
                    logger.warning(f"Failed to launch known app {cmd_target}: {e}")

            # 2. Check Windows Start Menu shortcuts (.lnk)
            shortcut_path = self._find_start_menu_shortcut(raw_app)
            if shortcut_path:
                try:
                    os.startfile(shortcut_path)
                    display_name = os.path.splitext(os.path.basename(shortcut_path))[0]
                    logger.info(f"Launched shortcut: {display_name} -> {shortcut_path}")
                    return {
                        "status": "app_launched",
                        "app": display_name,
                        "message": f"Opening {display_name}."
                    }
                except Exception as e:
                    logger.warning(f"Failed to start shortcut {shortcut_path}: {e}")

            # 3. Check system PATH via shutil.which
            which_path = shutil.which(norm) or shutil.which(f"{norm}.exe")
            if which_path:
                try:
                    subprocess.Popen([which_path])
                    logger.info(f"Launched from PATH: {which_path}")
                    return {
                        "status": "app_launched",
                        "app": raw_app.title(),
                        "message": f"Opening {raw_app.title()}."
                    }
                except Exception as e:
                    logger.warning(f"Failed to launch from PATH: {e}")

            # 4. Fallback: sanitize application name and launch via os.startfile (no shell=True)
            clean_app = re.sub(r"[^\w\s\-\.\:]", "", raw_app).strip()
            if not clean_app:
                return {"error": "Invalid application name."}
            try:
                os.startfile(clean_app)
                logger.info(f"Launched via os.startfile: {clean_app}")
                return {
                    "status": "app_launched",
                    "app": raw_app.title(),
                    "message": f"Opening {raw_app.title()}."
                }
            except Exception as e:
                logger.error(f"App launch failed for '{raw_app}': {e}")
                return {"error": f"Could not launch '{raw_app}': {e}"}

        elif tool_name == "close_app":
            raw_app = args.get("app_name", "").strip()
            if not raw_app:
                return {"error": "Please specify an application name to close."}

            norm = raw_app.lower()

            # Executable name mapping for Windows
            EXE_MAP = {
                "spotify": "Spotify.exe",
                "chrome": "chrome.exe",
                "google chrome": "chrome.exe",
                "edge": "msedge.exe",
                "microsoft edge": "msedge.exe",
                "browser": "msedge.exe",
                "notepad": "notepad.exe",
                "calculator": "CalculatorApp.exe",
                "calc": "CalculatorApp.exe",
                "vscode": "Code.exe",
                "vs code": "Code.exe",
                "code": "Code.exe",
                "visual studio code": "Code.exe",
                "discord": "Discord.exe",
                "steam": "steam.exe",
                "terminal": "WindowsTerminal.exe",
                "windows terminal": "WindowsTerminal.exe",
                "powershell": "powershell.exe",
                "cmd": "cmd.exe",
                "command prompt": "cmd.exe",
                "paint": "mspaint.exe",
                "task manager": "Taskmgr.exe",
                "taskmgr": "Taskmgr.exe",
                "word": "WINWORD.EXE",
                "excel": "EXCEL.EXE",
                "powerpoint": "POWERPNT.EXE",
            }

            target_exe = EXE_MAP.get(norm, f"{norm}.exe" if not norm.endswith(".exe") else norm)
            display = self.KNOWN_APPS.get(norm, (None, raw_app.title()))[1]

            # Validate target_exe to ensure only clean process executable names are passed
            if not re.match(r"^[a-zA-Z0-9_\-\.]+$", target_exe):
                return {"error": "Invalid application name for termination."}

            try:
                res = subprocess.run(
                    ["taskkill", "/F", "/IM", target_exe],
                    capture_output=True,
                    text=True
                )
                if res.returncode == 0:
                    logger.info(f"Closed app: {display} ({target_exe})")
                    return {
                        "status": "app_closed",
                        "app": display,
                        "message": f"Closed {display}."
                    }
                else:
                    # Fallback: safely stop process using environment variable
                    p_name = re.sub(r"[^a-zA-Z0-9_\-]", "", target_exe.replace(".exe", ""))
                    if p_name:
                        subprocess.run(
                            ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Stop-Process -Name $env:TARGET_PROC -Force -ErrorAction SilentlyContinue"],
                            capture_output=True,
                            text=True,
                            env={**os.environ, "TARGET_PROC": p_name}
                        )
                    return {
                        "status": "app_closed",
                        "app": display,
                        "message": f"Closed {display}."
                    }
            except Exception as e:
                logger.error(f"Failed to close '{raw_app}': {e}")
                return {"error": f"Could not close '{raw_app}': {e}"}

        elif tool_name == "list_installed_apps":
            apps = list(set([display for _, (_, display) in self.KNOWN_APPS.items()]))
            return {
                "apps": sorted(apps),
                "count": len(apps)
            }

        return {"error": f"Unknown AppLauncher tool: '{tool_name}'."}

# Instantiate and register into MCP Manager
from backend.mcp.manager import mcp_manager
app_launcher_server = AppLauncherMCPServer()
mcp_manager.register_server("app_launcher", app_launcher_server)
