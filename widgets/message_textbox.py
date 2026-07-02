import customtkinter as ctk


class MessageTextBox(ctk.CTkFrame):
    """Caja de texto reutilizable para mensajes personalizados con placeholder y envío por Enter."""

    def __init__(self, master=None, placeholder_text="Escribir mensaje personalizado...", height=4, command=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.placeholder_text = placeholder_text or ""
        self.submit_command = command
        self._placeholder_visible = False
        self._textbox_height_px = 50

        self.configure(height=self._textbox_height_px)
        self.pack_propagate(False)

        self.textbox = ctk.CTkTextbox(
            self,
            height=self._textbox_height_px,
            wrap="word",
            border_width=1,
            corner_radius=8,
            font=("Arial", 12),
            fg_color=("#FFFFFF", "#2B2B2B"),
            activate_scrollbars=True
        )
        self.textbox.pack(fill="both", expand=True, padx=0, pady=0)

        self.placeholder_label = ctk.CTkLabel(
            self,
            text=self.placeholder_text,
            font=("Arial", 12),
            text_color=("#8A8A8A", "#8A8A8A"),
            fg_color="transparent",
            anchor="w",
            # width=100,
            height=20
        )
        self.placeholder_label.place(x=8, y=8)
        self.placeholder_label.lift()
        self.placeholder_label.bind("<Button-1>", self._on_placeholder_click)

        self._tk_textbox = self.textbox._textbox
        self._apply_cursor_color()
        self.textbox.bind("<FocusIn>", self._on_focus_in)
        self.textbox.bind("<FocusOut>", self._on_focus_out)
        self.textbox.bind("<KeyPress>", self._on_key_press)
        self.textbox.bind("<Return>", self._on_return)
        self.textbox.bind("<Shift-Return>", self._on_shift_return)
        self._tk_textbox.bind("<FocusIn>", self._on_focus_in)
        self._tk_textbox.bind("<FocusOut>", self._on_focus_out)
        self._tk_textbox.bind("<Button-1>", self._on_click_textbox)
        self._tk_textbox.bind("<ButtonRelease-1>", self._on_button_release)
        self._tk_textbox.bind("<KeyRelease>", self._on_text_change)
        self._tk_textbox.bind("<Configure>", self._on_text_change)
        self._tk_textbox.bind("<B1-Motion>", self._on_mouse_drag)

        toplevel = self.winfo_toplevel()
        if toplevel is not None:
            toplevel.bind("<ButtonPress-1>", self._on_global_click, add='+')

        self._sync_placeholder()

    def _apply_cursor_color(self):
        try:
            appearance_mode = ctk.get_appearance_mode().lower()
            cursor_color = "#FFFFFF" if appearance_mode == "dark" else "#1F2933"
            self._tk_textbox.configure(insertbackground=cursor_color)
        except Exception:
            self._tk_textbox.configure(insertbackground="#1F2933")

    def update_theme(self):
        self._apply_cursor_color()
        self._sync_placeholder()

    def _on_placeholder_click(self, event=None):
        self.textbox.focus_set()
        self._hide_placeholder()
        return "break"

    def _on_click_textbox(self, event=None):
        self.textbox.focus_set()
        self._hide_placeholder()
        if event is not None:
            try:
                position = self._tk_textbox.index(f"@{event.x},{event.y}")
                self._tk_textbox.mark_set("insert", position)
                self._tk_textbox.see(position)
            except Exception:
                pass

    def _on_button_release(self, event=None):
        self.textbox.focus_set()

    def _on_mouse_drag(self, event=None):
        self.textbox.focus_set()

    def _on_global_click(self, event=None):
        if event is None:
            return

        widget = event.widget
        while widget is not None:
            if widget is self or widget is self.textbox or widget is self._tk_textbox or widget is self.placeholder_label:
                return
            widget = widget.master

        if self.focus_get() in (self._tk_textbox, self.textbox):
            try:
                self.winfo_toplevel().focus_set()
            except Exception:
                pass
        self._sync_placeholder()

    def _on_focus_in(self, event=None):
        self._apply_cursor_color()
        self._hide_placeholder()
        self.textbox.mark_set("insert", "1.0")

    def _on_focus_out(self, event=None):
        self._sync_placeholder()

    def _on_key_press(self, event=None):
        self._hide_placeholder()

    def _on_text_change(self, event=None):
        self.after(0, self._refresh_text_state)

    def _on_return(self, event=None):
        if self._placeholder_visible:
            self._hide_placeholder()

        if self.submit_command is not None:
            self.submit_command()
        return "break"

    def _on_shift_return(self, event=None):
        if self._placeholder_visible:
            self._hide_placeholder()

        self.textbox.insert("insert", "\n")
        self.textbox.see("end")
        self._refresh_text_state()
        return "break"

    def _hide_placeholder(self):
        self._placeholder_visible = False
        self.placeholder_label.place_forget()

    def _sync_placeholder(self):
        if not self.placeholder_text:
            self._placeholder_visible = False
            self.placeholder_label.place_forget()
            return

        current_text = self.textbox.get("1.0", "end-1c")
        if current_text:
            self._placeholder_visible = False
            self.placeholder_label.place_forget()
            return

        if self.focus_get() in (self._tk_textbox, self.textbox):
            self._placeholder_visible = False
            self.placeholder_label.place_forget()
            return

        self._placeholder_visible = True
        self.placeholder_label.place(x=8, y=8)

    def _refresh_text_state(self):
        if self._placeholder_visible:
            return

        try:
            self.textbox._check_if_scrollbars_needed()
        except Exception:
            pass

    def get_message(self):
        if self._placeholder_visible:
            return ""
        text = self.textbox.get("1.0", "end-1c")
        return text.strip() if text is not None else ""

    def clear(self):
        self.textbox.delete("1.0", "end")
        self._sync_placeholder()

    def has_real_text(self):
        message = self.get_message()
        return bool(message and message.strip())

    def focus_set(self):
        self.textbox.focus_set()
