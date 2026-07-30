import ctypes
import ctypes.wintypes
import os
import threading
import tkinter as tk
from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageOps, ImageSequence, ImageTk

from utils.resources import resource_path


AUTO_CLOSE_SECONDS = 11


class AlreadyRunningDialog(ctk.CTkToplevel):
    """Diálogo modal que avisa cuando la app ya está abierta."""

    def __init__(
        self,
        parent=None,
        gif_relative_path: str = "res/already_running.gif",
        auto_close_seconds: int = AUTO_CLOSE_SECONDS,
        anchor_hwnd: Optional[int] = None,
        anchor_geometry: Optional[dict] = None,
        dialog_width: int = 520,
        dialog_height: int = 560,
        message_y_offset: int = 10,
        button_y_offset: int = 12,
        button_width: int = 220,
    ):
        super().__init__(parent)
        self.parent = parent
        self.anchor_hwnd = anchor_hwnd
        self.anchor_geometry = anchor_geometry if isinstance(anchor_geometry, dict) else None
        self.gif_relative_path = gif_relative_path
        self.auto_close_seconds = max(1, auto_close_seconds)
        self.dialog_width = max(320, dialog_width)
        self.dialog_height = max(320, dialog_height)
        try:
            self._dpi_scale = ctk.ScalingTracker.get_window_scaling(self)
        except Exception:
            self._dpi_scale = 1.0
        self.gif_margin = 5
        self.gif_display_width = max(1, round(self.dialog_width * self._dpi_scale) - (self.gif_margin * 2))
        self.gif_display_height = 1
        self.message_y_offset = max(0, message_y_offset)
        self.button_y_offset = max(0, button_y_offset)
        self.button_width = max(140, button_width)
        self.frames = []
        self.frame_durations = []
        self.photo_frames = []
        self.current_frame_index = 0
        self._drag_offset_x = 0
        self._drag_offset_y = 0
        self._stop_event = threading.Event()
        self._countdown_thread = None
        self._after_id = None
        self._build_ui()
        self._load_gif()
        self._fit_height_to_content()
        self._start_animation()
        self._start_countdown()

    def _build_ui(self):
        self.title("Aplicación ya abierta")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.resizable(False, False)

        self.configure(fg_color="#0f172a")
        self.geometry(f"{self.dialog_width}x{self.dialog_height}")

        self.gif_container = tk.Frame(
            self,
            width=self.gif_display_width,
            height=self.gif_display_height,
            bg="#0f172a",
            bd=0,
            highlightthickness=0,
        )
        self.gif_container.pack(fill="x", padx=self.gif_margin, pady=(5, 5))
        self.gif_container.pack_propagate(False)

        self.label = tk.Label(
            self.gif_container,
            text="",
            bg="#0f172a",
            bd=0,
            highlightthickness=0,
            padx=0,
            pady=0,
        )
        self.label.pack(fill="both", expand=True)

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.container.grid_columnconfigure(0, weight=1)

        self.message_label = ctk.CTkLabel(
            self.container,
            text="Sólo puede haber una instancia de la aplicación!",
            font=ctk.CTkFont(size=14, weight="bold"),
            wraplength=max(260, self.dialog_width - 80),
            justify="center",
        )
        self.message_label.pack(fill="x", padx=16, pady=(self.message_y_offset, self.button_y_offset))

        self.btn_accept = ctk.CTkButton(
            self.container,
            text=f"Aceptar ({self.auto_close_seconds})",
            command=self.close_dialog,
            width=self.button_width,
            height=38,
            corner_radius=8,
        )
        self.btn_accept.pack(padx=16, pady=(0, 0))
        self._enable_dragging()

    def _enable_dragging(self):
        draggable_widgets = (
            self,
            self.gif_container,
            self.label,
            self.container,
            self.message_label,
        )

        for widget in draggable_widgets:
            widget.bind("<ButtonPress-1>", self._start_drag)
            widget.bind("<B1-Motion>", self._drag_window)

    def _start_drag(self, event):
        self._drag_offset_x = event.x_root - self.winfo_x()
        self._drag_offset_y = event.y_root - self.winfo_y()

    def _drag_window(self, event):
        x = event.x_root - self._drag_offset_x
        y = event.y_root - self._drag_offset_y
        self.geometry(f"{self.dialog_width}x{self.dialog_height}+{x}+{y}")

    def _fit_height_to_content(self):
        self.update_idletasks()
        required_height = self.winfo_reqheight()
        new_dialog_height = max(200, round(required_height / self._dpi_scale))
        self.dialog_height = new_dialog_height
        self.geometry(f"{self.dialog_width}x{self.dialog_height}")

    def _load_gif(self):
        try:
            path = resource_path(self.gif_relative_path)
            image = Image.open(path)
        except Exception:
            return

        try:
            image_width, image_height = image.size
            if image_width <= 0 or image_height <= 0:
                return

            self.gif_display_height = max(1, round(self.gif_display_width * image_height / image_width))
            target_size = (self.gif_display_width, self.gif_display_height)

            for frame in ImageSequence.Iterator(image):
                frame = frame.convert("RGBA")
                frame = ImageOps.contain(frame, target_size, method=Image.Resampling.LANCZOS)
                self.frames.append(frame)
                duration = frame.info.get("duration", 100)
                self.frame_durations.append(max(30, int(duration)))

            if self.frames:
                self.gif_container.configure(width=self.gif_display_width, height=self.gif_display_height)
                self.label.configure(width=self.gif_display_width, height=self.gif_display_height)
        except Exception:
            pass

    def _start_animation(self):
        if not self.frames:
            return

        self._animate_frame()

    def _animate_frame(self):
        if self._stop_event.is_set():
            return

        frame = self.frames[self.current_frame_index]
        rendered = ImageTk.PhotoImage(frame)
        self.photo_frames.append(rendered)
        if len(self.photo_frames) > 3:
            self.photo_frames.pop(0)
        self.label.configure(image=rendered)
        self.label.image = rendered

        self.current_frame_index += 1
        if self.current_frame_index >= len(self.frames):
            self.current_frame_index = 0

        self._after_id = self.after(self.frame_durations[self.current_frame_index - 1 if self.current_frame_index > 0 else 0], self._animate_frame)

    def _start_countdown(self):
        self._countdown_thread = threading.Thread(target=self._countdown_loop, daemon=True)
        self._countdown_thread.start()

    def _countdown_loop(self):
        remaining = self.auto_close_seconds
        while remaining >= 0 and not self._stop_event.is_set():
            self.after(0, lambda value=remaining: self.btn_accept.configure(text=f"Aceptar ({value})"))
            if remaining == 0:
                self.after(0, self.close_dialog)
                break

            remaining -= 1
            self._stop_event.wait(1.0)

    def close_dialog(self):
        if self._stop_event.is_set():
            return

        self._stop_event.set()
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self.destroy()

        try:
            if self.master is not None:
                self.master.quit()
        except Exception:
            pass

    def _get_monitors(self):
        monitors = []

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

            def callback(hmonitor, hdc, rect, data):
                info = MONITORINFO()
                info.cbSize = ctypes.sizeof(MONITORINFO)
                if ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                    monitors.append({
                        "bounds": rect_to_tuple(info.rcMonitor),
                        "work": rect_to_tuple(info.rcWork),
                        "primary": bool(info.dwFlags & 1),
                    })
                return True

            monitor_enum_proc = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.POINTER(RECT),
                ctypes.c_void_p,
            )
            ctypes.windll.user32.EnumDisplayMonitors(0, 0, monitor_enum_proc(callback), 0)
        except Exception:
            monitors = []

        if not monitors:
            monitors.append({
                "bounds": (0, 0, self.winfo_screenwidth(), self.winfo_screenheight()),
                "work": (0, 0, self.winfo_screenwidth(), self.winfo_screenheight()),
                "primary": True,
            })

        return monitors

    def _get_primary_monitor(self, monitors):
        for monitor in monitors:
            if monitor.get("primary"):
                return monitor
        return monitors[0]

    def _get_monitor_for_geometry(self, x, y, width, height, monitors):
        best_monitor = None
        best_area = 0

        for monitor in monitors:
            left, top, right, bottom = monitor["bounds"]
            inter_width = max(min(x + width, right) - max(x, left), 0)
            inter_height = max(min(y + height, bottom) - max(y, top), 0)
            area = inter_width * inter_height
            if area > best_area:
                best_area = area
                best_monitor = monitor

        return best_monitor or self._get_primary_monitor(monitors)

    def _clamp_to_monitor_work_area(self, x, y, width, height, monitor):
        left, top, right, bottom = monitor["work"]
        x = min(max(x, left), max(left, right - width))
        y = min(max(y, top), max(top, bottom - height))
        return x, y

    def _position_from_saved_geometry(self, dialog_w, dialog_h):
        if not self.anchor_geometry:
            return False

        try:
            parent_x = int(self.anchor_geometry["x"])
            parent_y = int(self.anchor_geometry["y"])
            parent_w = int(self.anchor_geometry["width"])
            parent_h = int(self.anchor_geometry["height"])
        except (KeyError, TypeError, ValueError):
            return False

        monitors = self._get_monitors()
        monitor = self._get_monitor_for_geometry(parent_x, parent_y, parent_w, parent_h, monitors)
        x = parent_x + max(0, (parent_w - dialog_w) // 2)
        y = parent_y + max(0, (parent_h - dialog_h) // 2)
        x, y = self._clamp_to_monitor_work_area(x, y, dialog_w, dialog_h, monitor)
        self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
        return True

    def show_over_parent(self):
        self.update_idletasks()
        dialog_w = self.dialog_width
        dialog_h = self.dialog_height
        positioned = False

        if self.anchor_hwnd:
            try:
                rect = ctypes.wintypes.RECT()
                if ctypes.windll.user32.GetWindowRect(self.anchor_hwnd, ctypes.byref(rect)):
                    parent_x = rect.left
                    parent_y = rect.top
                    parent_w = rect.right - rect.left
                    parent_h = rect.bottom - rect.top
                    x = parent_x + max(0, (parent_w - dialog_w) // 2)
                    y = parent_y + max(0, (parent_h - dialog_h) // 2)
                    self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
                    positioned = True
            except Exception:
                pass

        if self.parent is not None:
            self.transient(self.parent)
            self.grab_set()

        if not positioned:
            positioned = self._position_from_saved_geometry(dialog_w, dialog_h)

        if not positioned:
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            x = max(0, (screen_w - dialog_w) // 2)
            y = max(0, (screen_h - dialog_h) // 2)
            self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")

        self.lift()
        self.focus_force()
        self.deiconify()
        self.wait_visibility()
