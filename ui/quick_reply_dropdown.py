import customtkinter as ctk
from PIL import Image, ImageFilter

from utils.resources import resource_path

MENU_BUTTON_HEIGHT_RATIO = 0.50


class QuickReplySplitButton(ctk.CTkButton):
    """Boton rapido con accion principal y submenu opcional separado."""

    def __init__(
        self,
        master,
        text,
        image,
        submenu_config,
        command,
        submenu_command,
        height=82,
        **style
    ):
        self.text = text
        self.image = image
        self.submenu_config = submenu_config or {}
        self.command = command
        self.submenu_command = submenu_command
        self.menu_popup = None
        self.expanded_paths = set()
        self._pressed_main = False
        self._pressed_menu = False
        self._style = dict(style)
        self._current_fg_color = style["fg_color"]
        self._external_enter = None
        self._external_leave = None
        self._hover_inside = False
        self._leave_after_id = None
        super().__init__(
            master,
            text=text,
            image=image,
            command=command,
            fg_color=style["fg_color"],
            hover_color=style.get("hover_color", style["fg_color"]),
            hover=False,
            border_width=style.get("border_width", 2),
            border_color=style["border_color"],
            corner_radius=style.get("corner_radius", 18),
            height=height,
            font=style.get("font", ("Arial", 20, "bold")),
            anchor="w",
            compound="left"
        )

        menu_button_height = max(26, int(height * MENU_BUTTON_HEIGHT_RATIO))
        self._menu_button_size = menu_button_height
        self._refresh_menu_images()
        self.menu_button = ctk.CTkButton(
            self,
            text="",
            image=self._menu_icon_normal,
            command=None,
            fg_color=style["fg_color"],
            hover=False,
            text_color=self._icon_color(),
            border_width=0,
            width=50,
            height=50,
            # height=menu_button_height,
            corner_radius=0,
            # compound="left"
        )
        self.menu_button.place(
            relx=1,
            rely=0.5,
            anchor="e",
            x=-6,
            # relwidth=0.7,
            # relheight=0.7
        )
        self.menu_button.bind("<Enter>", self._on_menu_icon_enter)
        self.menu_button.bind("<Leave>", self._on_menu_icon_leave)
        self.menu_button.bind("<ButtonPress-1>", self._on_menu_press)
        self.menu_button.bind("<ButtonRelease-1>", self._on_menu_release)
        self.menu_button.bind("<Leave>", self._on_menu_leave, add="+")
        self._bind_pointer_tracking()

    def set_visual_state(self, fg_color, text_color, border_color):
        self.configure(
            fg_color=fg_color,
            hover_color=fg_color,
            text_color=text_color,
            border_color=border_color
        )
        self.menu_button.configure(
            fg_color=fg_color,
            text_color=self._icon_color()
        )
        self._refresh_menu_images()
        self.menu_button.configure(image=self._menu_icon_normal)

    def set_hover_handlers(self, on_enter, on_leave):
        self._external_enter = on_enter
        self._external_leave = on_leave

    def _bind_pointer_tracking(self):
        for widget in (self, self.menu_button):
            widget.bind("<Enter>", self._on_pointer_enter_or_motion, add="+")
            widget.bind("<Motion>", self._on_pointer_enter_or_motion, add="+")
            widget.bind("<Leave>", self._schedule_pointer_leave_check, add="+")

    def _on_pointer_enter_or_motion(self, event=None):
        self._cancel_leave_check()
        if not self._hover_inside:
            self._hover_inside = True
            if self._external_enter is not None:
                self._external_enter(event)

    def _schedule_pointer_leave_check(self, event=None):
        self._cancel_leave_check()
        self._leave_after_id = self.after(35, self._check_pointer_leave)

    def _check_pointer_leave(self):
        self._leave_after_id = None
        if self._pointer_inside_self():
            return

        if self._hover_inside:
            self._hover_inside = False
            if self._external_leave is not None:
                self._external_leave(None)

    def _cancel_leave_check(self):
        if self._leave_after_id is None:
            return

        try:
            self.after_cancel(self._leave_after_id)
        except Exception:
            pass
        self._leave_after_id = None

    def _pointer_inside_self(self):
        try:
            x, y = self.winfo_pointerxy()
            left = self.winfo_rootx()
            top = self.winfo_rooty()
            right = left + self.winfo_width()
            bottom = top + self.winfo_height()
        except Exception:
            return False

        return left <= x <= right and top <= y <= bottom

    def _on_menu_press(self, event):
        self._pressed_menu = True
        return "break"

    def _on_menu_release(self, event):
        if self._pressed_menu and self._event_inside_widget(event, self.menu_button):
            self.toggle_menu()
        self._pressed_menu = False
        return "break"

    def _on_menu_leave(self, event):
        self._pressed_menu = False

    def _event_inside_widget(self, event, widget):
        try:
            x = event.x_root
            y = event.y_root
            left = widget.winfo_rootx()
            top = widget.winfo_rooty()
            right = left + widget.winfo_width()
            bottom = top + widget.winfo_height()
        except Exception:
            return False
        return left <= x <= right and top <= y <= bottom

    def close_menu(self):
        if self.menu_popup is None:
            return
        try:
            self.menu_popup.destroy()
        except Exception:
            pass
        self.menu_popup = None

    def _get_menu_icon_path(self):
        appearance = ctk.get_appearance_mode().lower()
        if appearance == "dark":
            return "res/arrow_menu_dark.png"
        return "res/arrow_menu_light.png"

    def _refresh_menu_images(self):
        image_path = resource_path(self._get_menu_icon_path())
        base = Image.open(image_path).convert("RGBA")
        glow = base.filter(ImageFilter.GaussianBlur(1.5))

        self._menu_icon_normal = ctk.CTkImage(
            light_image=base,
            dark_image=base,
            size=(self._menu_button_size, self._menu_button_size)
        )
        self._menu_icon_hover = ctk.CTkImage(
            light_image=glow,
            dark_image=glow,
            size=(self._menu_button_size, self._menu_button_size)
        )

    def _on_menu_icon_enter(self, event):
        self.menu_button.configure(image=self._menu_icon_hover)

    def _on_menu_icon_leave(self, event):
        self.menu_button.configure(image=self._menu_icon_normal)

    def toggle_menu(self):
        if self.menu_popup is not None and self.menu_popup.winfo_exists():
            self.close_menu()
            return

        self.menu_popup = ctk.CTkToplevel(self)
        self.menu_popup.overrideredirect(True)
        self.menu_popup.attributes("-topmost", True)
        self.menu_popup.bind("<FocusOut>", lambda event: self.close_menu())
        self._position_menu()
        self._render_menu()
        self.menu_popup.focus_force()

    def _position_menu(self):
        self.update_idletasks()
        width = min(max(self.winfo_width() - 12, 260), 420)
        height = 360
        x = self.menu_button.winfo_rootx()
        y = self.menu_button.winfo_rooty() + self.menu_button.winfo_height() + 6
        self.menu_popup.geometry(f"{width}x{height}+{x}+{y}")

    def _render_menu(self):
        for child in self.menu_popup.winfo_children():
            child.destroy()

        container = ctk.CTkScrollableFrame(
            self.menu_popup,
            fg_color=self._menu_bg_color(),
            border_width=1,
            border_color=("#CBD5E1", "#111827"),
            corner_radius=8
        )
        container.pack(fill="both", expand=True)

        for index, item in enumerate(self.submenu_config.get("items", [])):
            self._render_item(container, item, (index,), level=0, category_image=None)

    def _render_item(self, parent, item, path, level, category_image):
        label = item.get("label", "")
        if not label:
            return

        children = item.get("items") if isinstance(item.get("items"), list) else []
        has_children = bool(children)
        is_expanded = path in self.expanded_paths
        prefix = "▾ " if is_expanded else "▸ " if has_children else ""
        text = f"{prefix}{label}"

        row = ctk.CTkButton(
            parent,
            text=text,
            height=32,
            fg_color=self._menu_bg_color(),
            hover_color=("#E2E8F0", "#374151"),
            text_color=("#111827", "#F8FAFC"),
            anchor="w",
            corner_radius=6,
            font=("Arial", 13, "bold" if level == 0 else "normal"),
            command=lambda item=item, path=path, category_image=category_image: self._on_item_click(item, path, category_image)
        )
        row.pack(fill="x", padx=(8 + level * 16, 8), pady=(6 if level == 0 else 2, 0))

        if is_expanded:
            next_category_image = item.get("category_image") or item.get("image") or category_image
            for index, child in enumerate(children):
                self._render_item(parent, child, path + (index,), level + 1, next_category_image)

    def _on_item_click(self, item, path, category_image):
        children = item.get("items") if isinstance(item.get("items"), list) else []
        if children:
            if path in self.expanded_paths:
                self.expanded_paths.remove(path)
            else:
                self.expanded_paths.add(path)
            self._render_menu()
            return

        payload = {
            "label": item.get("label", ""),
            "image": item.get("image"),
            "category_image": item.get("category_image") or category_image,
            "default_image": self.submenu_config.get("default_image"),
            "path": self._labels_for_path(path)
        }
        self.close_menu()
        self.submenu_command(payload)

    def _labels_for_path(self, path):
        labels = []
        items = self.submenu_config.get("items", [])
        for index in path:
            if index >= len(items):
                break
            item = items[index]
            labels.append(item.get("label", ""))
            items = item.get("items") if isinstance(item.get("items"), list) else []
        return [label for label in labels if label]

    def _icon_color(self):
        return "#FFFFFF" if ctk.get_appearance_mode().lower() == "dark" else "#1F2933"

    def _menu_bg_color(self):
        return ("#F8FAFC", "#1F2933")

    def _labels_for_path(self, path):
        labels = []
        items = self.submenu_config.get("items", [])
        for index in path:
            if index >= len(items):
                break
            item = items[index]
            labels.append(item.get("label", ""))
            items = item.get("items") if isinstance(item.get("items"), list) else []
        return [label for label in labels if label]

    def _event_inside_widget(self, event, widget):
        try:
            x = event.x_root
            y = event.y_root
            left = widget.winfo_rootx()
            top = widget.winfo_rooty()
            right = left + widget.winfo_width()
            bottom = top + widget.winfo_height()
        except Exception:
            return False
        return left <= x <= right and top <= y <= bottom

    def _icon_color(self):
        return "#FFFFFF" if ctk.get_appearance_mode().lower() == "dark" else "#1F2933"

    def _menu_bg_color(self):
        return ("#F8FAFC", "#1F2933")
