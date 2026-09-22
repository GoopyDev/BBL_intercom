import os

import customtkinter as ctk
from PIL import Image, ImageOps

from utils.resources import resource_path


class QuickReplyImagePopup(ctk.CTkToplevel):
    """Popup independiente para imagenes especificas de submenus."""

    def __init__(self, master, image_options, anchor_window, size=(180, 180), alpha=0.88):
        super().__init__(master)
        self.image_options = image_options or {}
        self.anchor_window = anchor_window
        self.size = size
        self.popup_image = None
        self.popup_pil_image = None
        self._closing = False
        self._close_after_id = None
        self._anchor_configure_callback = self._on_anchor_configure

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", alpha)

        self.configure(fg_color=("#F8FAFC", "#111827"))
        self._bind_to_anchor()
        self._position()
        self._build()

    def _bind_to_anchor(self):
        if self.anchor_window is None:
            return
        try:
            self.anchor_window.bind("<Configure>", self._anchor_configure_callback)
            self.anchor_window.bind("<Destroy>", self._on_anchor_destroy)
        except Exception:
            pass

    def _on_anchor_destroy(self, event=None):
        try:
            self.close_animation()
        except Exception:
            try:
                self.destroy()
            except Exception:
                pass

    def _on_anchor_configure(self, event=None):
        if self._closing or self.anchor_window is None:
            return
        try:
            if self.anchor_window.winfo_exists():
                self._position()
        except Exception:
            pass

    def _position(self):
        width, height = self.size
        try:
            anchor_x = int(self.anchor_window.current_x)
            anchor_y = int(self.anchor_window.current_y)
            anchor_w = int(self.anchor_window.width)
        except Exception:
            anchor_x = self.winfo_screenwidth() - width - 390
            anchor_y = self.winfo_screenheight() - height - 70
            anchor_w = 360

        x = anchor_x - width - 10
        if x < 10:
            x = anchor_x + anchor_w + 10
        y = max(anchor_y + 20, 10)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build(self):
        self.popup_image = self._load_first_valid_image()
        if self.popup_image is None:
            self.destroy()
            return

        label = ctk.CTkLabel(
            self,
            text="",
            image=self.popup_image,
            fg_color=("#F8FAFC", "#111827")
        )
        label.pack(fill="both", expand=True)

    def _load_first_valid_image(self):
        for key in ("image", "category_image", "default_image"):
            image_name = self.image_options.get(key)
            if not image_name:
                continue

            path = resource_path(os.path.join("res", image_name))
            if not os.path.exists(path):
                continue

            try:
                image = Image.open(path)
                image = ImageOps.contain(image.convert("RGBA"), self.size, method=Image.Resampling.LANCZOS)
                self.popup_pil_image = image
                return ctk.CTkImage(
                    light_image=image,
                    dark_image=image,
                    size=self.size
                )
            except Exception as e:
                print(f"Error cargando imagen de submenu '{image_name}': {e}")

        return None

    def close_animation(self):
        if self._closing:
            return
        self._closing = True
        self._animate_close()

    def _animate_close(self):
        self._close_after_id = None
        try:
            alpha = float(self.attributes("-alpha"))
        except Exception:
            alpha = 0

        if alpha > 0.04:
            self.attributes("-alpha", max(alpha - 0.08, 0))
            self._close_after_id = self.after(16, self._animate_close)
        else:
            self.destroy()

    def destroy(self):
        if self._close_after_id is not None:
            try:
                self.after_cancel(self._close_after_id)
            except Exception:
                pass
            self._close_after_id = None

        try:
            if self.anchor_window is not None:
                self.anchor_window.unbind("<Configure>", self._anchor_configure_callback)
                self.anchor_window.unbind("<Destroy>", self._on_anchor_destroy)
        except Exception:
            pass

        try:
            super().destroy()
        except Exception:
            pass
