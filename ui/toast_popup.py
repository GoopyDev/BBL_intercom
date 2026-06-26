import os

import customtkinter as ctk
from PIL import Image

from config.constants import BOTONES_PRESET, FONDOS_POPUP
from utils.resources import resource_path


ROTACION_FONDOS = {}
MENSAJES_RAPIDOS = {boton["texto"] for boton in BOTONES_PRESET}
COLOR_POPUP_FONDO = ("#CBD5E1", "#202123")
COLOR_POPUP_BORDE = ("#A8B0BA", "#FFFFFF")
COLOR_POPUP_TEXTO = ("#1F2933", "#FFFFFF")
COLOR_POPUP_CONTENEDOR = ("#F5F7FA", "#333333")
DESPLAZAMIENTO_POPUP = 20
POPUPS_ANTES_DE_REINICIAR_POSICION = 5


def obtener_fondo_popup(mensaje):
    """Devuelve el siguiente fondo configurado para el mensaje recibido."""
    fondos = FONDOS_POPUP.get(mensaje)

    if not fondos:
        return None

    idx = ROTACION_FONDOS.get(mensaje, 0)
    fondo = fondos[idx]
    idx += 1

    if idx >= len(fondos):
        idx = 0

    ROTACION_FONDOS[mensaje] = idx
    return fondo


class ToastPopup(ctk.CTkToplevel):
    """Notificacion flotante con soporte para respuestas."""
    ultima_posicion = None
    contador_posicion = 0

    def __init__(self, master, remitente, mensaje, on_reply=None):
        super().__init__(master)

        self.mensaje_data = self._normalizar_mensaje(remitente, mensaje)
        self.mensaje_texto = self.mensaje_data["text"]
        self.remitente = self.mensaje_data["from_alias"] or remitente
        self.on_reply = on_reply
        self.es_mensaje_rapido = self.mensaje_texto in MENSAJES_RAPIDOS and not self.mensaje_data.get("reply_to")

        self.width = 360
        self.height = 200 if self.es_mensaje_rapido else 280

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        if ToastPopup.ultima_posicion:
            base_x, base_y = ToastPopup.ultima_posicion
        else:
            base_x = screen_w - self.width - 20
            base_y = screen_h - self.height - 60

        offset = ToastPopup.contador_posicion * DESPLAZAMIENTO_POPUP
        x = base_x + offset
        y = base_y + offset
        ToastPopup.contador_posicion = (
            ToastPopup.contador_posicion + 1
        ) % POPUPS_ANTES_DE_REINICIAR_POSICION

        self.current_x = x
        self.target_x = x
        self.current_y = y + 20
        self.target_y = y
        self.geometry(f"{self.width}x{self.height}+{x}+{self.current_y}")
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_window_x = x
        self.drag_window_y = self.current_y
        self.dragging = False

        self.main = ctk.CTkFrame(
            self,
            fg_color=COLOR_POPUP_FONDO,
            border_width=5,
            border_color=COLOR_POPUP_BORDE,
            width=self.width,
            height=self.height
        )
        self.main.place(x=0, y=0)
        self._bind_drag(self)
        self._bind_drag(self.main)

        self.bg_image = None
        self.bg_pil_image = None
        self.bg_label = None
        self.scroll_frame = None
        self.reply_button = None
        self.reply_frame = None
        self.reply_entry = None

        fondo = obtener_fondo_popup(self.mensaje_texto)
        if fondo:
            self._crear_fondo(fondo)

        if self.es_mensaje_rapido:
            self._crear_contenido_rapido(self.remitente, self.mensaje_texto)
        else:
            self._crear_contenido_personalizado()

        self.close_btn = ctk.CTkButton(
            self.main,
            text="X",
            text_color=COLOR_POPUP_TEXTO,
            width=28,
            height=28,
            fg_color="transparent",
            bg_color="transparent",
            hover_color="#D33",
            command=self.close_animation
        )
        self.close_btn.place(x=325, y=6)

        if self.bg_label is not None:
            self.bg_label.lift()
        self.title_label.lift()
        if self.scroll_frame is not None:
            self.scroll_frame.lift()
        if self.reply_button is not None:
            self.reply_button.lift()
        if self.reply_frame is not None:
            self.reply_frame.lift()
        self.msg_label.lift()
        self.close_btn.lift()

        self.fade_in()

    def _normalizar_mensaje(self, remitente, mensaje):
        if isinstance(mensaje, dict):
            return {
                "id": mensaje.get("id"),
                "from_hostname": mensaje.get("from_hostname"),
                "from_alias": mensaje.get("from_alias") or remitente,
                "text": mensaje.get("text") or "",
                "reply_to": mensaje.get("reply_to") if isinstance(mensaje.get("reply_to"), dict) else None
            }

        return {
            "id": None,
            "from_hostname": None,
            "from_alias": remitente,
            "text": mensaje,
            "reply_to": None
        }

    def _crear_fondo(self, fondo):
        try:
            fondo_path = resource_path(os.path.join("res", fondo))
            self.bg_pil_image = Image.open(fondo_path)
            self.bg_image = ctk.CTkImage(
                light_image=self.bg_pil_image,
                dark_image=self.bg_pil_image,
                size=(self.width, self.height)
            )
            self.bg_label = ctk.CTkLabel(
                self.main,
                image=self.bg_image,
                text="",
                width=self.width,
                height=self.height
            )
            self.bg_label.place(x=0, y=0)
            self._bind_drag(self.bg_label)
        except Exception as e:
            print(f"Error cargando fondo: {e}")

    def _crear_contenido_rapido(self, remitente, mensaje):
        self.title_label = ctk.CTkLabel(
            self.main,
            text=remitente,
            font=("Consolas", 15, "bold"),
            anchor="w",
            text_color="#FFFFFF",
            fg_color="#000000",
            bg_color="#000000"
        )
        self.title_label.place(x=40, y=145)
        self._bind_drag(self.title_label)

        self.msg_label = ctk.CTkLabel(
            self.main,
            text=mensaje,
            font=("Consolas", 13),
            justify="left",
            wraplength=240,
            anchor="w",
            text_color="#FFFFFF",
            fg_color="#000000",
            bg_color="#000000"
        )
        self.msg_label.place(x=100, y=168)
        self._bind_drag(self.msg_label)

    def _crear_contenido_personalizado(self):
        self.title_label = ctk.CTkLabel(
            self.main,
            text=self.remitente,
            font=("Consolas", 14, "bold"),
            anchor="w",
            width=275,
            text_color=COLOR_POPUP_TEXTO
        )
        self.title_label.place(x=18, y=14)
        self._bind_drag(self.title_label)

        self.contenedor_limite = ctk.CTkFrame(
            self.main,
            width=320,
            height=155,
            fg_color=COLOR_POPUP_CONTENEDOR
        )
        self.contenedor_limite.place(x=18, y=48)
        self.contenedor_limite.pack_propagate(False)

        self.scroll_frame = ctk.CTkScrollableFrame(
            self.contenedor_limite,
            fg_color="transparent"
        )
        self.scroll_frame.pack(fill="both", expand=True)

        respuesta_a = self.mensaje_data.get("reply_to")
        if respuesta_a:
            preview_sender = respuesta_a.get("from_alias") or "Mensaje original"
            preview_text = respuesta_a.get("text") or ""
            self.preview_label = ctk.CTkLabel(
                self.scroll_frame,
                text=f"{preview_sender}: {preview_text}",
                font=("Consolas", 11),
                justify="left",
                wraplength=285,
                anchor="nw",
                text_color=("#4B5563", "#CBD5E1"),
                fg_color=("#E2E8F0", "#242424"),
                corner_radius=6
            )
            self.preview_label.pack(fill="x", padx=(0, 10), pady=(0, 8))

        self.msg_label = ctk.CTkLabel(
            self.scroll_frame,
            text=self.mensaje_texto,
            font=("Consolas", 13),
            justify="left",
            wraplength=295,
            anchor="nw",
            text_color=COLOR_POPUP_TEXTO
        )
        self.msg_label.pack(fill="x", expand=True, padx=(0, 10), pady=0)

        self.reply_button = ctk.CTkButton(
            self.main,
            text="Responder",
            width=110,
            height=30,
            command=self.mostrar_respuesta
        )
        self.reply_button.place(x=18, y=220)

        if not self.mensaje_data.get("from_hostname") or self.on_reply is None:
            self.reply_button.configure(state="disabled", text="Sin respuesta")

    def mostrar_respuesta(self):
        if self.reply_frame is not None:
            return

        self.reply_button.place_forget()
        self.reply_frame = ctk.CTkFrame(self.main, fg_color="transparent", width=320, height=58)
        self.reply_frame.place(x=18, y=204)
        self.reply_frame.grid_columnconfigure(0, weight=1)

        preview = self._resumen_texto(self.mensaje_texto, 70)
        ctk.CTkLabel(
            self.reply_frame,
            text=f"Respondiendo a {self.remitente}: {preview}",
            font=("Consolas", 10),
            anchor="w",
            text_color=COLOR_POPUP_TEXTO
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        self.reply_entry = ctk.CTkEntry(
            self.reply_frame,
            placeholder_text="Escribir respuesta...",
            height=30
        )
        self.reply_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.reply_entry.focus_set()
        self.reply_entry.bind("<Return>", lambda event: self.enviar_respuesta())

        ctk.CTkButton(
            self.reply_frame,
            text="Enviar",
            width=70,
            height=30,
            command=self.enviar_respuesta
        ).grid(row=1, column=1)

    def enviar_respuesta(self):
        if self.reply_entry is None or self.on_reply is None:
            return

        texto = self.reply_entry.get().strip()
        if not texto:
            return

        self.on_reply(self.mensaje_data, texto)
        self.close_animation()

    def _resumen_texto(self, texto, largo):
        texto = " ".join((texto or "").split())
        if len(texto) <= largo:
            return texto
        return f"{texto[:largo - 3]}..."

    def _bind_drag(self, widget):
        widget.bind("<ButtonPress-1>", self.start_drag)
        widget.bind("<B1-Motion>", self.do_drag)
        widget.bind("<ButtonRelease-1>", self.end_drag)

    def start_drag(self, event):
        self.dragging = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.drag_window_x = self.current_x
        self.drag_window_y = self.current_y

    def do_drag(self, event):
        new_x = self.drag_window_x + (event.x_root - self.drag_start_x)
        new_y = self.drag_window_y + (event.y_root - self.drag_start_y)

        self.current_x = new_x
        self.target_x = new_x
        self.current_y = new_y
        self.target_y = new_y
        self.geometry(f"{self.width}x{self.height}+{new_x}+{new_y}")

    def end_drag(self, event):
        self.dragging = False
        self.current_x = self.target_x
        self.current_y = self.target_y
        self.target_x = self.current_x
        self.target_y = self.current_y
        ToastPopup.ultima_posicion = (int(self.current_x), int(self.current_y))
        ToastPopup.contador_posicion = 0

    def fade_in(self):
        alpha = self.attributes("-alpha")

        if alpha < 0.98:
            alpha += 0.06
            self.attributes("-alpha", alpha)

            if not self.dragging and self.current_y > self.target_y:
                self.current_y -= 2

            self.geometry(
                f"{self.width}x{self.height}+"
                f"{int(self.current_x)}+{int(self.current_y)}"
            )
            self.after(16, self.fade_in)

    def close_animation(self):
        alpha = self.attributes("-alpha")

        if alpha > 0.02:
            alpha -= 0.06
            self.attributes("-alpha", alpha)

            self.current_y += 3
            self.width -= 1
            self.height -= 1

            self.geometry(
                f"{self.width}x{self.height}+"
                f"{int(self.current_x)}+{int(self.current_y)}"
            )
            self.after(16, self.close_animation)
        else:
            self.destroy()
