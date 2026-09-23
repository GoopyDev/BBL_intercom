import ctypes

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
        self._outside_click_binding_id = None
        self._window_change_binding_ids = []
        self._native_wndproc = None
        self._native_previous_wndproc = None
        self._native_hook_hwnd = None
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

        # Botón de menú con command directo a toggle_menu
        self.menu_button = ctk.CTkButton(
            self,
            text="",
            image=self._menu_icon_normal,
            command=self.toggle_menu,
            fg_color=style["fg_color"],
            hover=False,
            text_color=self._icon_color(),
            border_width=0,
            width=50,
            height=50,
            corner_radius=0,
        )
        self.menu_button.place(
            relx=1,
            rely=0.5,
            anchor="e",
            x=-6,
        )
        self.menu_button.bind("<Enter>", self._on_menu_icon_enter)
        self.menu_button.bind("<Leave>", self._on_menu_icon_leave)
        
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

    def close_menu(self):
        if self.menu_popup is None:
            return
        self._unbind_outside_click()
        self._unbind_window_changes()
        self._uninstall_native_click_hook()
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
        try:
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
        except Exception as e:
            print(f"[ERROR] No se pudo cargar la imagen del menú: {e}")
            self._menu_icon_normal = None
            self._menu_icon_hover = None

    def _on_menu_icon_enter(self, event):
        if self._menu_icon_hover:
            self.menu_button.configure(image=self._menu_icon_hover)

    def _on_menu_icon_leave(self, event):
        if self._menu_icon_normal:
            self.menu_button.configure(image=self._menu_icon_normal)

    def toggle_menu(self):
        # Crear un menú nativo de Tkinter
        import tkinter as tk

        appearance = ctk.get_appearance_mode().lower()
        if appearance == "dark":
            bg_color = "#2B2B2B"
            fg_color = "#F8FAFC"
            active_bg = "#374151"
            active_fg = "#FFFFFF"
        else:
            bg_color = "#F8FAFC"
            fg_color = "#111827"
            active_bg = "#E2E8F0"
            active_fg = "#111827"

        # Crear la estructura de menú nativa de Tkinter
        menu = tk.Menu(
            self,
            tearoff=0,
            bg=bg_color,
            fg=fg_color,
            activebackground=active_bg,
            activeforeground=active_fg,
            bd=1,
            relief="flat",
            font=("Arial", 10)
        )

        items = self.submenu_config.get("items", [])
        if not items:
            menu.add_command(label="Sin opciones disponibles", state="disabled")
        else:
            self._build_native_menu(menu, items, level=0, category_image=None)

        # Calcular posición en pantalla justo debajo del botón de menú
        self.update_idletasks()
        x = self.menu_button.winfo_rootx()
        y = self.menu_button.winfo_rooty() + self.menu_button.winfo_height() + 4

        # Mostrar el menú en pantalla (Tk handles focus, clicks & titlebar automatically)
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    # def toggle_menu(self):
    #     if self.menu_popup is not None and self.menu_popup.winfo_exists():
    #         self.close_menu()
    #         return

    #     self.menu_popup = ctk.CTkToplevel(self)
    #     self.menu_popup.overrideredirect(True)
    #     self.menu_popup.attributes("-topmost", True)
        
    #     # Permitir cerrar el popup presionando ESC
    #     self.menu_popup.bind("<Escape>", lambda event: self.close_menu())

    #     self._position_menu()
    #     self._render_menu()
    #     self._raise_menu()
    #     self.menu_popup.after(5, self._raise_menu)
    #     self.after_idle(self._bind_outside_click)
    #     self.after_idle(self._bind_window_changes)
    #     self.after_idle(self._install_native_click_hook)

    def _build_native_menu(self, parent_menu, items, level, category_image):
        import tkinter as tk

        appearance = ctk.get_appearance_mode().lower()
        bg_color = "#2B2B2B" if appearance == "dark" else "#F8FAFC"
        fg_color = "#F8FAFC" if appearance == "dark" else "#111827"
        active_bg = "#374151" if appearance == "dark" else "#E2E8F0"
        active_fg = "#FFFFFF" if appearance == "dark" else "#111827"

        for index, item in enumerate(items):
            label = item.get("label", "")
            if not label:
                continue

            children = item.get("items") if isinstance(item.get("items"), list) else []
            next_cat_img = item.get("category_image") or item.get("image") or category_image

            if children:
                # Es una categoría / submenú
                submenu = tk.Menu(
                    parent_menu,
                    tearoff=0,
                    bg=bg_color,
                    fg=fg_color,
                    activebackground=active_bg,
                    activeforeground=active_fg,
                    bd=1,
                    relief="flat",
                    font=("Arial", 10)
                )
                self._build_native_menu(submenu, children, level + 1, next_cat_img)
                parent_menu.add_cascade(label=label, menu=submenu)
            else:
                # Es una opción seleccionable
                payload = {
                    "label": label,
                    "image": item.get("image"),
                    "category_image": next_cat_img,
                    "default_image": self.submenu_config.get("default_image"),
                    "path": [label]
                }
                parent_menu.add_command(
                    label=label,
                    command=lambda p=payload: self.submenu_command(p)
                )

    def _bind_outside_click(self):
        if self.menu_popup is None or self._outside_click_binding_id is not None:
            return
        app_window = self.winfo_toplevel()
        self._outside_click_binding_id = app_window.bind(
            "<ButtonPress-1>",
            self._on_application_click,
            add="+"
        )

    def _unbind_outside_click(self):
        if self._outside_click_binding_id is None:
            return
        try:
            self.winfo_toplevel().unbind(
                "<ButtonPress-1>",
                self._outside_click_binding_id
            )
        except Exception:
            pass
        self._outside_click_binding_id = None

    def _bind_window_changes(self):
        if self.menu_popup is None or self._window_change_binding_ids:
            return
        app_window = self.winfo_toplevel()
        for sequence in ("<Configure>", "<FocusIn>"):
            binding_id = app_window.bind(
                sequence,
                self._on_window_change,
                add="+"
            )
            self._window_change_binding_ids.append((sequence, binding_id))

    def _unbind_window_changes(self):
        if not self._window_change_binding_ids:
            return
        app_window = self.winfo_toplevel()
        for sequence, binding_id in self._window_change_binding_ids:
            try:
                app_window.unbind(sequence, binding_id)
            except Exception:
                pass
        self._window_change_binding_ids = []

    def _on_window_change(self, event=None):
        if self.menu_popup is not None and self.menu_popup.winfo_exists():
            self.close_menu()

    # def _install_native_click_hook(self):
    #     if self.menu_popup is None or self._native_wndproc is not None:
    #         return
    #     try:
    #         hwnd = self.winfo_toplevel().winfo_id()
            
    #         # Definición formal para Win64 / Win32
    #         wndproc_type = ctypes.WINFUNCTYPE(
    #             ctypes.c_ssize_t,
    #             ctypes.c_void_p,  # hwnd
    #             ctypes.c_uint,    # msg
    #             ctypes.c_size_t,  # wparam
    #             ctypes.c_ssize_t   # lparam
    #         )

    #         # Configurar firmas explícitas de la API de Windows para evitar desbordamiento en x64
    #         call_window_proc = ctypes.windll.user32.CallWindowProcW
    #         call_window_proc.argtypes = [
    #             ctypes.c_void_p,  # lpPrevWndFunc
    #             ctypes.c_void_p,  # hWnd
    #             ctypes.c_uint,    # Msg
    #             ctypes.c_size_t,  # wParam
    #             ctypes.c_ssize_t   # lParam
    #         ]
    #         call_window_proc.restype = ctypes.c_ssize_t

    #         set_window_long_ptr = ctypes.windll.user32.SetWindowLongPtrW
    #         set_window_long_ptr.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    #         set_window_long_ptr.restype = ctypes.c_ssize_t

    #         NC_CLICK_MESSAGES = {0x00A1, 0x00A4}  # WM_NCLBUTTONDOWN, WM_NCRBUTTONDOWN

    #         def window_proc(window, message, wparam, lparam):
    #             if message in NC_CLICK_MESSAGES:
    #                 if self.menu_popup is not None:
    #                     self.close_menu()

    #             return call_window_proc(
    #                 ctypes.c_void_p(self._native_previous_wndproc),
    #                 ctypes.c_void_p(window),
    #                 message,
    #                 wparam,
    #                 lparam
    #             )

    #         self._native_wndproc = wndproc_type(window_proc)
    #         self._native_previous_wndproc = set_window_long_ptr(
    #             ctypes.c_void_p(hwnd),
    #             -4,  # GWLP_WNDPROC
    #             ctypes.cast(self._native_wndproc, ctypes.c_void_p)
    #         )
    #         self._native_hook_hwnd = hwnd
    #     except Exception as e:
    #         print(f"[ERROR] No se pudo instalar el hook nativo: {e}")
    #         self._native_wndproc = None
    #         self._native_previous_wndproc = None
    #         self._native_hook_hwnd = None

    # def _uninstall_native_click_hook(self):
    #     if self._native_wndproc is None or self._native_hook_hwnd is None:
    #         return
    #     try:
    #         set_window_long_ptr = ctypes.windll.user32.SetWindowLongPtrW
    #         set_window_long_ptr.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    #         set_window_long_ptr.restype = ctypes.c_ssize_t

    #         set_window_long_ptr(
    #             ctypes.c_void_p(self._native_hook_hwnd),
    #             -4,
    #             ctypes.c_void_p(self._native_previous_wndproc)
    #         )
    #     except Exception as e:
    #         print(f"[ERROR] No se pudo desinstalar el hook nativo: {e}")
    #     finally:
    #         self._native_wndproc = None
    #         self._native_previous_wndproc = None
    #         self._native_hook_hwnd = None


    def _on_application_click(self, event):
        if self.menu_popup is None or not self.menu_popup.winfo_exists():
            return
        if self._event_inside_popup(event):
            return
        self.close_menu()

    def _event_inside_popup(self, event):
        try:
            left = self.menu_popup.winfo_rootx()
            top = self.menu_popup.winfo_rooty()
            right = left + self.menu_popup.winfo_width()
            bottom = top + self.menu_popup.winfo_height()
            return left <= event.x_root <= right and top <= event.y_root <= bottom
        except Exception:
            return False

    def _raise_menu(self):
        if self.menu_popup is None:
            return
        try:
            if self.menu_popup.winfo_exists():
                self.menu_popup.lift()
        except Exception:
            pass

    def _get_monitor_work_area(self, x, y, width, height):
        try:
            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long)
                ]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("rcMonitor", RECT),
                    ("rcWork", RECT),
                    ("dwFlags", ctypes.c_ulong)
                ]

            monitors = []

            def callback(hmonitor, hdc, monitor_rect, data):
                info = MONITORINFO()
                info.cbSize = ctypes.sizeof(MONITORINFO)
                if ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                    monitors.append((
                        info.rcMonitor.left,
                        info.rcMonitor.top,
                        info.rcMonitor.right,
                        info.rcMonitor.bottom,
                        info.rcWork.left,
                        info.rcWork.top,
                        info.rcWork.right,
                        info.rcWork.bottom
                    ))
                return True

            monitor_callback = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.POINTER(RECT),
                ctypes.c_void_p
            )
            ctypes.windll.user32.EnumDisplayMonitors(
                0, 0, monitor_callback(callback), 0
            )

            best_monitor = None
            best_area = 0
            for monitor in monitors:
                left, top, right, bottom = monitor[:4]
                overlap_width = max(min(x + width, right) - max(x, left), 0)
                overlap_height = max(min(y + height, bottom) - max(y, top), 0)
                area = overlap_width * overlap_height
                if area > best_area:
                    best_area = area
                    best_monitor = monitor

            if best_monitor is not None:
                return best_monitor[4:]
        except Exception:
            pass

        return (0, 0, self.winfo_screenwidth(), self.winfo_screenheight())

    def _position_menu(self):
        self.update_idletasks()
        self.menu_button.update_idletasks()
        width = min(max(self.winfo_width() - 12, 260), 420)
        height = 360
        button_x = int(self.menu_button.winfo_rootx())
        button_y = int(self.menu_button.winfo_rooty())
        button_width = int(self.menu_button.winfo_width())
        button_height = int(self.menu_button.winfo_height())
        work_left, work_top, work_right, work_bottom = self._get_monitor_work_area(
            button_x,
            button_y,
            button_width,
            button_height
        )

        x = min(max(button_x, work_left), max(work_left, work_right - width))
        below_y = button_y + button_height + 6
        above_y = button_y - height - 6
        if below_y + height <= work_bottom:
            y = below_y
        elif above_y >= work_top:
            y = above_y
        else:
            y = min(max(below_y, work_top), max(work_top, work_bottom - height))

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

        items = self.submenu_config.get("items", [])
        if not items:
            # Mensaje por si la estructura Categories está vacía o no tiene ítems
            lbl = ctk.CTkLabel(container, text="Sin opciones disponibles", font=("Arial", 12, "italic"))
            lbl.pack(padx=10, pady=10)
            return

        for index, item in enumerate(items):
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