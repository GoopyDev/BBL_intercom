import ctypes
import os
import sys
import tkinter as tk
from typing import Dict, Optional

from PIL import Image, ImageOps, ImageSequence, ImageTk

from utils.resources import resource_path


class SplashScreen:
    """Pantalla de bienvenida que reproduce un GIF animado antes de iniciar la app."""

    def __init__(
        self,
        gif_relative_path: str,
        last_geometry: Optional[Dict[str, int]] = None,
        fadeout_duration: int = 250,
        fadeout_steps: int = 10,
        playback_speed: float = 1.0,
        target_size: Optional[tuple[int, int]] = None,
    ):
        self.gif_relative_path = gif_relative_path
        self.last_geometry = last_geometry or {}
        self.fadeout_duration = fadeout_duration
        self.fadeout_steps = max(1, fadeout_steps)
        self.playback_speed = max(0.1, playback_speed)
        self.target_size = target_size
        self.root: Optional[tk.Tk] = None
        self.label: Optional[tk.Label] = None
        self.frames = []
        self.frame_durations = []
        self.photo_frames = []
        self.current_frame_index = 0
        self.alpha = 1.0
        self.loaded = self._load_gif()

    def _load_gif(self) -> bool:
        try:
            path = resource_path(self.gif_relative_path)
            image = Image.open(path)
        except Exception:
            return False

        try:
            for frame in ImageSequence.Iterator(image):
                frame = frame.convert("RGBA")
                if self.target_size is not None:
                    frame = ImageOps.contain(frame, self.target_size, method=Image.Resampling.LANCZOS)
                self.frames.append(frame)
                duration = frame.info.get("duration", 100)
                self.frame_durations.append(max(10, int(duration / self.playback_speed)))

            if not self.frames:
                return False

            self.width, self.height = self.frames[0].size
            if self.target_size is not None:
                self.width, self.height = self.target_size
            return True
        except Exception:
            return False

    def _obtener_monitores(self):
        monitores = []

        try:
            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("rcMonitor", RECT),
                    ("rcWork", RECT),
                    ("dwFlags", ctypes.c_ulong),
                ]

            def rect_to_tuple(rect):
                return rect.left, rect.top, rect.right, rect.bottom

            def callback(hmonitor, hdc, lprc, data):
                info = MONITORINFO()
                info.cbSize = ctypes.sizeof(MONITORINFO)
                if ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                    monitores.append({
                        "bounds": rect_to_tuple(info.rcMonitor),
                        "work": rect_to_tuple(info.rcWork),
                        "primary": bool(info.dwFlags & 1),
                    })
                return True

            MonitorEnumProc = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.POINTER(RECT),
                ctypes.c_void_p,
            )

            ctypes.windll.user32.EnumDisplayMonitors(0, 0, MonitorEnumProc(callback), 0)
        except Exception:
            pass

        if not monitores:
            screen_width = self._screen_width()
            screen_height = self._screen_height()
            monitores.append({
                "bounds": (0, 0, screen_width, screen_height),
                "work": (0, 0, screen_width, screen_height),
                "primary": True,
            })

        return monitores

    def _screen_width(self) -> int:
        if self.root:
            try:
                return self.root.winfo_screenwidth()
            except Exception:
                return 800

        temp_root = None
        try:
            temp_root = tk.Tk()
            temp_root.withdraw()
            return temp_root.winfo_screenwidth()
        except Exception:
            return 800
        finally:
            if temp_root is not None:
                temp_root.destroy()

    def _screen_height(self) -> int:
        if self.root:
            try:
                return self.root.winfo_screenheight()
            except Exception:
                return 600

        temp_root = None
        try:
            temp_root = tk.Tk()
            temp_root.withdraw()
            return temp_root.winfo_screenheight()
        except Exception:
            return 600
        finally:
            if temp_root is not None:
                temp_root.destroy()

    def _obtener_monitor_principal(self, monitores):
        for monitor in monitores:
            if monitor.get("primary"):
                return monitor
        return monitores[0]

    def _obtener_monitor_por_geometria(self, x, y, width, height, monitores):
        mejor_monitor = None
        mejor_area = 0

        for monitor in monitores:
            left, top, right, bottom = monitor["bounds"]
            inter_width = max(min(x + width, right) - max(x, left), 0)
            inter_height = max(min(y + height, bottom) - max(y, top), 0)
            area = inter_width * inter_height
            if area > mejor_area:
                mejor_area = area
                mejor_monitor = monitor

        return mejor_monitor or self._obtener_monitor_principal(monitores)

    def _geometria_valida(self, geometry):
        return (
            isinstance(geometry, dict)
            and all(isinstance(geometry.get(k), int) for k in ("x", "y", "width", "height"))
        )

    def _calcular_posicion(self):
        monitores = self._obtener_monitores()
        monitor = self._obtener_monitor_principal(monitores)

        if self._geometria_valida(self.last_geometry):
            monitor = self._obtener_monitor_por_geometria(
                self.last_geometry["x"],
                self.last_geometry["y"],
                self.last_geometry["width"],
                self.last_geometry["height"],
                monitores,
            )

        left, top, right, bottom = monitor["work"]
        x = left + max((right - left - self.width) // 2, 0)
        y = top + max((bottom - top - self.height) // 2, 0)
        return x, y

    def show(self):
        if not self.loaded:
            return

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        x, y = self._calcular_posicion()
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")

        self.label = tk.Label(self.root, bg="black")
        self.label.pack(expand=True, fill="both")

        self._show_frame()
        self.root.mainloop()

    def _show_frame(self):
        self.photo_frames.clear()
        frame = self.frames[self.current_frame_index]
        rendered = ImageTk.PhotoImage(frame)
        self.photo_frames.append(rendered)
        self.label.configure(image=rendered)

        duration = self.frame_durations[self.current_frame_index]
        self.current_frame_index += 1

        if self.current_frame_index >= len(self.frames):
            self.root.after(duration, self._start_fadeout)
        else:
            self.root.after(duration, self._show_frame)

    def _start_fadeout(self):
        try:
            self.root.attributes("-alpha", 1.0)
        except Exception:
            self._destroy_splash()
            return

        self._fade_step(self.fadeout_steps)

    def _fade_step(self, remaining_steps):
        if remaining_steps <= 0:
            self._destroy_splash()
            return

        self.alpha = max(0.0, self.alpha - 1.0 / self.fadeout_steps)
        try:
            self.root.attributes("-alpha", self.alpha)
        except Exception:
            self._destroy_splash()
            return

        delay = max(10, self.fadeout_duration // self.fadeout_steps)
        self.root.after(delay, lambda: self._fade_step(remaining_steps - 1))

    def _destroy_splash(self):
        try:
            self.root.destroy()
        except Exception:
            pass
        self.root = None
