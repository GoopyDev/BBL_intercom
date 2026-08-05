import customtkinter as ctk


class Tooltip:
    """Tooltip reutilizable para widgets de customtkinter.

    Uso: Tooltip(widget, "texto", delay=400, position='below', offset_x=0, offset_y=4)

    `position` puede ser 'below' (por defecto) o 'above'. `offset_x` y `offset_y`
    permiten ajustar el desplazamiento final.
    """

    def __init__(self, widget, texto, delay=400, position="below", offset_x=0, offset_y=4):
        self.widget = widget
        self.texto = texto
        self.delay = int(delay) if delay is not None else 400
        self.position = position if position in ("below", "above") else "below"
        self.offset_x = int(offset_x)
        self.offset_y = int(offset_y)

        self._after_id = None
        self._toplevel = None
        self._label = None
        self._tag = None

        # Intentar insertar un bindtag propio al inicio para ejecutar
        # nuestros handlers antes que otros que devuelvan "break".
        try:
            tag = f"Tooltip{hex(id(self))}"
            current_tags = self.widget.bindtags()
            if tag not in current_tags:
                self.widget.bindtags((tag,) + tuple(current_tags))
            self._tag = tag
            # bindear a la clase/tag para garantizar prioridad
            self.widget.bind_class(tag, "<Enter>", self._on_enter, add="+")
            self.widget.bind_class(tag, "<Leave>", self._on_leave, add="+")
            self.widget.bind_class(tag, "<Button-1>", self._on_click, add="+")
            self.widget.bind_class(tag, "<Destroy>", lambda e: self._ocultar(), add="+")
        except Exception:
            # fallback a binds normales si algo falla
            self.widget.bind("<Enter>", self._on_enter, add="+")
            self.widget.bind("<Leave>", self._on_leave, add="+")
            self.widget.bind("<Button-1>", self._on_click, add="+")
            self.widget.bind("<Destroy>", lambda e: self._ocultar(), add="+")

    def _on_enter(self, event=None):
        self._cancel_show()
        try:
            self._after_id = self.widget.after(self.delay, self._mostrar)
        except Exception:
            self._after_id = None

    def _on_leave(self, event=None):
        self._cancel_show()
        self._ocultar()

    def _on_click(self, event=None):
        self._ocultar()

    def _cancel_show(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _mostrar(self):
        if self._toplevel is not None:
            return

        try:
            root = self.widget.winfo_toplevel()
            self._toplevel = ctk.CTkToplevel(root)
            self._toplevel.overrideredirect(True)
            try:
                self._toplevel.attributes("-topmost", True)
            except Exception:
                pass

            self._label = ctk.CTkLabel(self._toplevel, text=self.texto)
            self._label.pack(ipadx=6, ipady=3)

            # posicionar debajo del widget, centrado; usar try/except si no está listo
            try:
                widget_rootx = self.widget.winfo_rootx()
                widget_rooty = self.widget.winfo_rooty()
                widget_w = self.widget.winfo_width()
                widget_h = self.widget.winfo_height()

                # forzar cálculo de tamaño del label
                self._label.update_idletasks()
                label_w = self._label.winfo_width()
                label_h = self._label.winfo_height()

                x = widget_rootx + (widget_w // 2) - (label_w // 2) + self.offset_x

                if self.position == "below":
                    y = widget_rooty + widget_h + self.offset_y
                else:  # above
                    y = widget_rooty - label_h - self.offset_y

                self._toplevel.geometry(f"+{x}+{y}")
            except Exception:
                # si falla el cálculo, dejar que el gestor coloque la ventana
                pass
        except Exception:
            self._toplevel = None

    def _ocultar(self):
        self._cancel_show()
        if self._toplevel is not None:
            try:
                self._toplevel.destroy()
            except Exception:
                pass
            self._toplevel = None
