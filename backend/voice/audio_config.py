import os
import sys
import logging
from typing import Dict, Any, List

logger = logging.getLogger("daisy.voice.audio_config")

def apply_windows_audio_optimizations() -> Dict[str, Any]:
    """
    Applies Windows-specific audio optimizations:
    1. Sets UserDuckingPreference = 3 ("Do nothing") in Windows Registry
       so Windows never ducks or filters Spotify audio during microphone capture.
    2. Sets ScreenReaderDuckingPreference = 0.
    3. Configures WebView2 Chromium arguments to prevent WASAPI raw capture degradation.
    """
    result = {
        "ducking_disabled": False,
        "webview2_flags_set": False,
        "devices": []
    }

    if sys.platform == "win32":
        # 1. Registry: Disable Windows Communications Ducking (UserDuckingPreference = 3)
        try:
            import winreg
            key_path = r"Software\Microsoft\Multimedia\Audio"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                # 3 = "Do nothing" (0 = 80% volume reduction, 1 = 50%, 2 = Mute all other sounds, 3 = Do nothing)
                winreg.SetValueEx(key, "UserDuckingPreference", 0, winreg.REG_DWORD, 3)
                winreg.SetValueEx(key, "ScreenReaderDuckingPreference", 0, winreg.REG_DWORD, 0)
                logger.info("[AudioConfig] Windows Communications Audio Ducking successfully set to 'Do nothing' (3).")
                result["ducking_disabled"] = True
        except Exception as e:
            logger.warning(f"[AudioConfig] Could not set Windows ducking registry preference: {e}")

        # 2. Configure WebView2 browser arguments
        try:
            current_args = os.environ.get("WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS", "")
            audio_args = "--disable-features=WASAPIRawAudioCapture --autoplay-policy=no-user-gesture-required --enable-features=WebRtcAllowInputVolumeModification"
            if "WASAPIRawAudioCapture" not in current_args:
                os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = f"{current_args} {audio_args}".strip()
            result["webview2_flags_set"] = True
            logger.info("[AudioConfig] WebView2 audio optimization flags configured.")
        except Exception as e:
            logger.warning(f"[AudioConfig] Could not set WebView2 audio arguments: {e}")

        # 3. Audit active audio devices
        result["devices"] = audit_audio_devices()

    return result

def audit_audio_devices() -> List[Dict[str, Any]]:
    """
    Audits audio input devices on Windows to detect potential
    Bluetooth Hands-Free Profile (HFP) conflicts.
    """
    devices = []
    if sys.platform != "win32":
        return devices

    try:
        import subprocess
        cmd = [
            "powershell", "-NoProfile", "-Command",
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
            "Get-PnpDevice -Class 'AudioEndpoint' -Status 'OK' | "
            "Select-Object FriendlyName, InstanceId | ConvertTo-Json"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        if res.returncode == 0 and res.stdout.strip():
            import json
            data = json.loads(res.stdout)
            if isinstance(data, dict):
                data = [data]
            for item in data:
                name = item.get("FriendlyName", "")
                is_handsfree = any(k in name.lower() for k in ["hands-free", "handsfree", "hfp", "bthhfenum"])
                devices.append({
                    "name": name,
                    "is_bluetooth_handsfree": is_handsfree,
                })
    except Exception as e:
        logger.debug(f"[AudioConfig] Device audit note: {e}")

    return devices
