import datetime
import os
import tkinter as tk

import customtkinter as ctk
import time
from PIL import Image, ImageEnhance, ImageOps

from config.constants import BOTONES_PRESET, FONDOS_POPUP
from utils.resources import resource_path
from ui.quick_reply_image_popup import QuickReplyImagePopup
from ui.coin_jump_animation import (
    AnimacionSaltoMoneda,
    IndicadorRecargaSalto,
    RECARGA_SALTO_THRESHOLD_MS,
    RECARGA_SALTO_RATE_MS_PER_PX,
    RECARGA_SALTO_MAX_EXTRA_PX,
)
from ui.tooltip import Tooltip


ROTACION_FONDOS = {}
MENSAJES_RAPIDOS = {boton["texto"] for boton in BOTONES_PRESET}
IMAGENES_BOTONES_RAPIDOS = {boton["texto"]: boton["img"] for boton in BOTONES_PRESET}
COLOR_POPUP_FONDO = ("#CBD5E1", "#202123")
COLOR_POPUP_BORDE = ("#A8B0BA", "#151515")
COLOR_POPUP_TEXTO = ("#1F2933", "#FFFFFF")
COLOR_POPUP_CONTENEDOR = ("#F5F7FA", "#333333")
COLOR_POPUP_TIMESTMP = "#D4AF37"
DESPLAZAMIENTO_POPUP = 20
POPUPS_ANTES_DE_REINICIAR_POSICION = 5
POSICION_MENSAJE_RAPIDO_ALIAS = {"x": 33, "y": 165}
POSICION_MENSAJE_RAPIDO = {"x": 100, "y": 194}
POSICION_TIMESTMP_RAPIDO = {"x": 15, "y": 196}
POSICION_TIMESTMP_PERSONALIZADO = {"x": 205, "y": 220, "width": 135}
MARGEN_POPUP_X = 18

ANCHO_NOTIFICACION = 360    # Ancho total del toast notification
ALTO_NOTIFICACION = 220  # Alto base del toast notification

ANCHO_CONTENIDO_POPUP = 320

# RESPUESTAS
ANCHO_RESPUESTA_RAPIDA = 328
ALTO_RESPUESTA_RAPIDA = 140
POSICION_REPLY_FRAME_Y = 128
ALTO_VISTA_PREVIA_REPLY = 70
ANCHO_BOTON_ENVIAR = 70
SEPARACION_INPUT_BOTON = 6
PADDING_INTERNO_REPLY = 8  # separación entre el borde blanco del "reply_frame" y el contenido
ANCHO_INPUT_RESPUESTA_PERSONALIZADA = (ANCHO_CONTENIDO_POPUP - ANCHO_BOTON_ENVIAR - SEPARACION_INPUT_BOTON - (PADDING_INTERNO_REPLY * 2)) # <- nuevo: deja hueco para el padding izq/der
ANCHO_INPUT_RESPUESTA_RAPIDA = ANCHO_RESPUESTA_RAPIDA - 20 - ANCHO_BOTON_ENVIAR - SEPARACION_INPUT_BOTON

FUENTE_ICONO_COPIAR = ("Segoe UI Symbol", 16)
ANCHO_BOTON_COPIAR = 34
ALTO_BOTON_COPIAR = 30
ICONO_COPIAR = "📋"
ICONO_COPIADO = "✓"

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

    def __init__(self, master, remitente, mensaje, on_reply=None, available_destinations=None):
        super().__init__(master)

        self.mensaje_data = self._normalizar_mensaje(remitente, mensaje)
        self.mensaje_texto = self.mensaje_data["text"]
        self.remitente = self.mensaje_data["from_alias"] or remitente
        self.on_reply = on_reply
        self.es_mensaje_rapido = self.mensaje_texto in MENSAJES_RAPIDOS and not self.mensaje_data.get("reply_to")
        self.quick_reply_submenu = self.mensaje_data.get("quick_reply_submenu")
        self.destinatarios = self.mensaje_data.get("to") or []
        respuesta_original = self.mensaje_data.get("reply_to") or {}
        if not self.destinatarios and isinstance(respuesta_original.get("to"), list):
            self.destinatarios = respuesta_original["to"]
        self.available_destinations = list(available_destinations or [])
        self._destinatario_aliases = {
            str(item.get("hostname")).strip().upper(): item.get("alias") or item.get("hostname")
            for item in self.available_destinations
            if isinstance(item, dict) and item.get("hostname")
        }
        self.reply_destinations = None
        self.reply_is_forward = False
        self._reply_menu = None

        self.width = 360
        self.height = ALTO_NOTIFICACION if self.es_mensaje_rapido else ALTO_NOTIFICACION + 50

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
        self._closing = False
        self._fade_after_id = None
        self._close_after_id = None
        self._close_btn_pressed = False
        self._send_btn_pressed = False

        self.main = ctk.CTkFrame(
            self,
            fg_color=COLOR_POPUP_FONDO,
            border_width=5,
            border_color=COLOR_POPUP_BORDE,
            width=self.width,
            height=self.height
        )
        self.main.place(x=0, y=0)
        self.bind("<Button-2>", self._on_middle_click)
        self.bind("<ButtonPress-2>", self._on_middle_click)
        self.main.bind("<Button-2>", self._on_middle_click)
        self.main.bind("<ButtonPress-2>", self._on_middle_click)
        self._bind_drag(self)
        self._bind_drag(self.main)

        self.bg_image = None
        self.bg_pil_image = None
        self.bg_label = None
        self.scroll_frame = None
        self.message_reply_preview = None
        self.reply_button = None
        self.reply_frame = None
        self.reply_entry = None
        self.reply_preview = None
        self.reply_text_var = None
        self.reply_error_label = None
        self.copy_button = None
        self.copy_tooltip = None
        self.msg_text_widget = None
        self._copy_btn_pressed = False
        # contador de presión (ms) para la funcionalidad "Recarga de salto"
        self._copy_press_start_ms = None
        self._last_copy_press_duration_ms = 0
        self._recarga_indicator = None
        self._copy_original_fg_color = None
        self._copy_original_hover_color = None
        self._copy_is_gold = False
        self._recarga_update_after_id = None
        self._recarga_hide_after_id = None
        self.reply_error_after_id = None
        self.send_button = None
        self.quick_reply_image = None
        self.quick_reply_image_popup = None
        self._reply_btn_pressed = False

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
            hover_color="#D33"
        )
        self.close_btn.place(x=325, y=6)
        self.close_btn.bind("<ButtonPress-1>", self._on_close_press)
        self.close_btn.bind("<ButtonRelease-1>", self._on_close_release)
        self.close_btn.bind("<B1-Motion>", self._stop_interactive_drag)
        self.close_btn.bind("<Leave>", self._on_close_leave)

        if self.bg_label is not None:
            self.bg_label.lift()
        self.title_label.lift()
        if getattr(self, "destinatarios_label", None) is not None:
            self.destinatarios_label.lift()
        if self.scroll_frame is not None:
            self.scroll_frame.lift()
        if self.reply_button is not None:
            self.reply_button.lift()
        if getattr(self, "reply_menu_button", None) is not None:
            self.reply_menu_button.lift()
        if self.reply_frame is not None:
            self.reply_frame.lift()
        self.msg_label.lift()
        if getattr(self, "timestamp_label", None) is not None:
            self.timestamp_label.lift()
        self.close_btn.lift()

        self._mostrar_imagen_submenu_si_corresponde()
        self.fade_in()

    def _normalizar_mensaje(self, remitente, mensaje):
        if isinstance(mensaje, dict):
            return {
                "id": mensaje.get("id"),
                "from_hostname": mensaje.get("from_hostname"),
                "from_alias": mensaje.get("from_alias") or remitente,
                "text": mensaje.get("text") or "",
                "to": mensaje.get("to") if isinstance(mensaje.get("to"), list) else [],
                "created_at": mensaje.get("created_at"),
                "reply_to": mensaje.get("reply_to") if isinstance(mensaje.get("reply_to"), dict) else None,
                "quick_reply_submenu": mensaje.get("quick_reply_submenu") if isinstance(mensaje.get("quick_reply_submenu"), dict) else None
            }

        return {
            "id": None,
            "from_hostname": None,
            "from_alias": remitente,
            "text": mensaje,
            "to": [],
            "created_at": None,
            "reply_to": None,
            "quick_reply_submenu": None
        }

    def _mostrar_imagen_submenu_si_corresponde(self):
        if not self.es_mensaje_rapido or not isinstance(self.quick_reply_submenu, dict):
            return

        try:
            self.quick_reply_image_popup = QuickReplyImagePopup(
                self.master,
                self.quick_reply_submenu,
                self
            )
        except Exception as e:
            print(f"Error mostrando imagen de submenu: {e}")
            self.quick_reply_image_popup = None

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

    def _formatear_timestamp(self, tipo):
        created_at = self.mensaje_data.get("created_at")
        if not created_at:
            return ""

        try:
            if isinstance(created_at, datetime.datetime):
                dt = created_at
            else:
                dt = datetime.datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return ""

        if tipo == "rapido":
            return dt.strftime("%d/%m %H:%M")

        return f"{dt.strftime('%d/%m/%Y')}\n{dt.strftime('%H:%M')}"

    def _crear_label_destinatarios(self, x, y):
        contenedor = ctk.CTkFrame(
            self.main,
            width=64,
            height=28,
            fg_color=("#EEF2F7", "#1F2937"),
            corner_radius=8,
            border_width=1,
            border_color=("#CBD5E1", "#374151")
        )
        contenedor.place(x=x, y=y)
        contenedor.bind("<ButtonPress-1>", self._stop_interactive_drag)
        contenedor.bind("<B1-Motion>", self._stop_interactive_drag)
        contenedor.bind("<ButtonRelease-1>", self._stop_interactive_drag)
        label = ctk.CTkLabel(
            contenedor,
            text="Para 🛈",
            font=("Segoe UI", 11, "bold"),
            anchor="center",
            fg_color="transparent",
            text_color=("#1F2933", "#F8FAFC"),
            height=30
        )
        label.pack(fill="both", expand=True, padx=5)
        try:
            self.destinatarios_tooltip = Tooltip(
                contenedor,
                self._texto_destinatarios(),
                position="above",
                offset_y=6,
                scrollable=True,
                max_width=280,
                max_height=160
            )
        except Exception:
            self.destinatarios_tooltip = None
        return contenedor

    def _crear_contenido_rapido(self, remitente, mensaje):
        self.title_label = ctk.CTkLabel(
            self.main,
            text=remitente,
            font=("Consolas", 15, "bold"),
            height=1,
            anchor="w",
            text_color="#FFFFFF",
            fg_color="#000000",
            bg_color="#000000"
        )
        self.title_label.place(
            x=POSICION_MENSAJE_RAPIDO_ALIAS["x"],
            y=POSICION_MENSAJE_RAPIDO_ALIAS["y"]
        )
        self._bind_drag(self.title_label)

        self.destinatarios_label = self._crear_label_destinatarios(18, 14)
        self._crear_acciones_respuesta(92, 14, 100)

        self.msg_label = ctk.CTkLabel(
            self.main,
            text=mensaje,
            font=("Consolas", 13),
            height=1,
            justify="left",
            wraplength=240,
            anchor="w",
            text_color="#FFFFFF",
            fg_color="#000000",
            bg_color="#000000"
        )
        self.msg_label.place(x=POSICION_MENSAJE_RAPIDO["x"], y=POSICION_MENSAJE_RAPIDO["y"])
        self._bind_drag(self.msg_label)

        self.timestamp_label = ctk.CTkLabel(
            self.main,
            text=self._formatear_timestamp("rapido"),
            font=("Consolas", 10, "bold"),
            height=1,
            justify="left",
            anchor="w",
            text_color=COLOR_POPUP_TIMESTMP,
            fg_color="#000000",
            bg_color="#000000"
        )
        self.timestamp_label.place(
            x=POSICION_TIMESTMP_RAPIDO["x"],
            y=POSICION_TIMESTMP_RAPIDO["y"]
        )
        self._bind_drag(self.timestamp_label)

        if not self.mensaje_data.get("from_hostname") or self.on_reply is None:
            self.reply_button.configure(state="disabled", text="Sin respuesta")
            self.reply_menu_button.configure(state="disabled")

    def _crear_contenido_personalizado(self):
        self.title_label = ctk.CTkLabel(
            self.main,
            text=self.remitente,
            font=("Consolas", 14, "bold"),
            anchor="w",
            width=180,
            height=1,
            text_color=COLOR_POPUP_TEXTO
        )
        self.title_label.place(x=18, y=14)
        self._bind_drag(self.title_label)
        self.destinatarios_label = self._crear_label_destinatarios(210, 10)
        self._crear_acciones_respuesta(18, 220, 110)

        self.contenedor_limite = ctk.CTkFrame(
            self.main,
            width=ANCHO_CONTENIDO_POPUP,
            height=155,
            fg_color=COLOR_POPUP_CONTENEDOR
        )
        self.contenedor_limite.place(x=MARGEN_POPUP_X, y=48)
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
            self.message_reply_preview = ctk.CTkTextbox(
                self.scroll_frame,
                width=295,
                height=48,
                font=("Consolas", 11),
                wrap="word",
                text_color=("#4B5563", "#CBD5E1"),
                fg_color=("#E2E8F0", "#242424"),
                corner_radius=6,
                border_width=0
            )
            self.message_reply_preview.insert("1.0", f"{preview_sender}: {preview_text}")
            self.message_reply_preview.configure(state="disabled")
            self.message_reply_preview.pack(fill="x", padx=(0, 10), pady=(0, 8))
            self.message_reply_preview.bind("<ButtonPress-1>", self._stop_text_input_drag)
            self.message_reply_preview.bind("<B1-Motion>", self._stop_text_input_drag)
            self.message_reply_preview.bind("<ButtonRelease-1>", self._stop_text_input_drag)

        self.msg_label = ctk.CTkTextbox(
            self.scroll_frame,
            width=295,
            height=90,
            font=("Consolas", 13),
            wrap="word",
            text_color=COLOR_POPUP_TEXTO,
            fg_color="transparent",
            border_width=0,
            corner_radius=0,
            activate_scrollbars=True,
            undo=False
        )
        self.msg_label.insert("1.0", self.mensaje_texto)
        self.msg_label.configure(state="normal")
        self.msg_label.pack(fill="x", expand=True, padx=(0, 10), pady=0)

        self.msg_text_widget = getattr(self.msg_label, "_textbox", self.msg_label)
        self.msg_text_widget.bind("<ButtonPress-1>", self._stop_text_input_drag)
        self.msg_text_widget.bind("<B1-Motion>", self._stop_text_input_drag)
        self.msg_text_widget.bind("<ButtonRelease-1>", self._stop_text_input_drag)
        self.msg_text_widget.bind("<Key>", self._on_message_text_key)
        self.msg_label.bind("<ButtonPress-1>", self._stop_text_input_drag)
        self.msg_label.bind("<B1-Motion>", self._stop_text_input_drag)
        self.msg_label.bind("<ButtonRelease-1>", self._stop_text_input_drag)
        self.msg_label.bind("<Key>", self._on_message_text_key)

        self.copy_button = ctk.CTkButton(
            self.main,
            text=ICONO_COPIAR,
            font=FUENTE_ICONO_COPIAR,
            width=ANCHO_BOTON_COPIAR,
            height=ALTO_BOTON_COPIAR,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            text_color="#FFFFFF",
            corner_radius=8
        )
        self.copy_button.place(x=164, y=220)
        self.copy_button.bind("<ButtonPress-1>", self._on_copy_press)
        self.copy_button.bind("<ButtonRelease-1>", self._on_copy_release)
        self.copy_button.bind("<B1-Motion>", self._stop_interactive_drag)
        self.copy_button.bind("<Leave>", self._on_copy_leave)
        try:
            self.copy_tooltip = Tooltip(self.copy_button, "Copiar", position="above", offset_y=6)
        except Exception:
            self.copy_tooltip = None

        try:
            self._recarga_indicator = IndicadorRecargaSalto(self.copy_button)
        except Exception:
            self._recarga_indicator = None

        # store original colors so we can restore after gold
        try:
            if getattr(self, 'copy_button', None) is not None:
                try:
                    self._copy_original_fg_color = self.copy_button.cget('fg_color')
                except Exception:
                    self._copy_original_fg_color = '#2563EB'
                try:
                    self._copy_original_hover_color = self.copy_button.cget('hover_color')
                except Exception:
                    self._copy_original_hover_color = '#1D4ED8'
        except Exception:
            self._copy_original_fg_color = self._copy_original_fg_color or '#2563EB'
            self._copy_original_hover_color = self._copy_original_hover_color or '#1D4ED8'

        self.timestamp_label = ctk.CTkLabel(
            self.main,
            text=self._formatear_timestamp("personalizado"),
            font=("Consolas", 10, "bold"),
            justify="right",
            anchor="e",
            width=POSICION_TIMESTMP_PERSONALIZADO["width"],
            text_color=COLOR_POPUP_TIMESTMP,
            fg_color="transparent",
            bg_color="transparent"
        )
        self.timestamp_label.place(
            x=POSICION_TIMESTMP_PERSONALIZADO["x"],
            y=POSICION_TIMESTMP_PERSONALIZADO["y"]
        )
        self._bind_drag(self.timestamp_label)

        if not self.mensaje_data.get("from_hostname") or self.on_reply is None:
            self.reply_button.configure(state="disabled", text="Sin respuesta")
            self.reply_menu_button.configure(state="disabled")

    def mostrar_respuesta(self):
        if self.reply_frame is not None:
            return

        self.reply_button.place_forget()
        if getattr(self, "timestamp_label", None) is not None:
            self.timestamp_label.place_forget()

        if self.es_mensaje_rapido:
            self._crear_respuesta_rapida()
        else:
            self._crear_respuesta_personalizada()

        self._configurar_controles_respuesta()

    def _crear_respuesta_personalizada(self):
        self.reply_frame = ctk.CTkFrame(
            self.main,
            fg_color="transparent",
            border_color="white",
            border_width=1,
            width=ANCHO_CONTENIDO_POPUP,
            height=ALTO_RESPUESTA_RAPIDA
        )
        self.reply_frame.place(x=MARGEN_POPUP_X, y=POSICION_REPLY_FRAME_Y)
        self.reply_frame.grid_propagate(False)
        self.reply_frame.grid_columnconfigure(0, weight=0, minsize=ANCHO_INPUT_RESPUESTA_PERSONALIZADA)
        self.reply_frame.grid_columnconfigure(1, weight=0, minsize=ANCHO_BOTON_ENVIAR)
        self.reply_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self.reply_frame,
            text=f"Respondiendo a {self.remitente}",
            font=("Consolas", 10),
            anchor="w",
            text_color=COLOR_POPUP_TEXTO,
            height=0
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=(PADDING_INTERNO_REPLY, PADDING_INTERNO_REPLY), pady=(PADDING_INTERNO_REPLY, 0))

        self._crear_preview_respuesta(
            texto=self.mensaje_texto,
            row=1,
            column=0,
            columnspan=2,
            width=ANCHO_CONTENIDO_POPUP - (PADDING_INTERNO_REPLY * 2),
            height=ALTO_VISTA_PREVIA_REPLY,
            padx=(PADDING_INTERNO_REPLY, PADDING_INTERNO_REPLY),
            pady=(2, 4),
            sticky="nsew"
        )

        self._crear_fila_input_respuesta(row=2, column=0, button_column=1)

    def _crear_respuesta_rapida(self):
        self.reply_frame = ctk.CTkFrame(
            self.main,
            fg_color=("#F8FAFC", "#1F2933"),
            border_width=1,
            border_color=("#CBD5E1", "#111827"),
            corner_radius=8,
            width=ANCHO_RESPUESTA_RAPIDA,
            height=150
        )
        self.reply_frame.place(x=16, y=42)
        self.reply_frame.grid_propagate(False)
        self.reply_frame.grid_columnconfigure(0, weight=0, minsize=58)
        self.reply_frame.grid_columnconfigure(1, weight=0, minsize=ANCHO_INPUT_RESPUESTA_RAPIDA - 58)
        self.reply_frame.grid_columnconfigure(2, weight=0, minsize=ANCHO_BOTON_ENVIAR)
        self.reply_frame.grid_rowconfigure(2, weight=1)

        miniatura = self._crear_miniatura_respuesta_rapida()
        if miniatura is not None:
            ctk.CTkLabel(
                self.reply_frame,
                image=miniatura,
                text="",
                width=54,
                height=54
            ).grid(row=0, column=0, rowspan=2, padx=(10, 8), pady=(10, 6), sticky="nw")

        ctk.CTkLabel(
            self.reply_frame,
            text=f"Respondiendo a {self.remitente}",
            font=("Consolas", 10, "bold"),
            anchor="w",
            text_color=COLOR_POPUP_TEXTO
        ).grid(row=0, column=1, columnspan=2, sticky="ew", padx=(0, 10), pady=(10, 0))

        self._crear_preview_respuesta(
            texto=self.mensaje_texto,
            row=1,
            column=1,
            columnspan=2,
            width=ANCHO_RESPUESTA_RAPIDA - 88,
            height=60,
            padx=(0, 10),
            pady=(0, 8)
        )

        self._crear_fila_input_respuesta(row=2, column=0, button_column=2, columnspan=2)

    def _crear_miniatura_respuesta_rapida(self):
        try:
            imagen = self.bg_pil_image
            if imagen is None:
                nombre_imagen = IMAGENES_BOTONES_RAPIDOS.get(self.mensaje_texto)
                if not nombre_imagen:
                    return None
                imagen = Image.open(resource_path(os.path.join("res", nombre_imagen)))

            miniatura = ImageOps.fit(imagen.convert("RGB"), (50, 50), method=Image.Resampling.LANCZOS)
            miniatura = ImageEnhance.Color(miniatura).enhance(0.18)
            self.quick_reply_image = ctk.CTkImage(
                light_image=miniatura,
                dark_image=miniatura,
                size=(50, 50)
            )
            return self.quick_reply_image
        except Exception as e:
            print(f"Error creando miniatura de respuesta: {e}")
            return None

    def _crear_preview_respuesta(self, texto, row, column, columnspan, width, height, padx, pady, sticky="ew"):
        self.reply_preview = ctk.CTkTextbox(
            self.reply_frame,
            width=width,
            height=height,
            font=("Consolas", 10),
            wrap="word",
            text_color=("#4B5563", "#CBD5E1"),
            fg_color=("#E2E8F0", "#242424"),
            corner_radius=6,
            border_width=0
        )
        self.reply_preview.insert("1.0", texto or "")
        self.reply_preview.configure(state="disabled")
        self.reply_preview.grid(
            row=row,
            column=column,
            columnspan=columnspan,
            sticky="ew",
            padx=padx,
            pady=pady
        )
        self.reply_preview.bind("<ButtonPress-1>", self._stop_text_input_drag)
        self.reply_preview.bind("<B1-Motion>", self._stop_text_input_drag)
        self.reply_preview.bind("<ButtonRelease-1>", self._stop_text_input_drag)

    def _crear_fila_input_respuesta(self, row, column, button_column, columnspan=1):
        self.reply_entry = ctk.CTkTextbox(
            self.reply_frame,
            width=ANCHO_INPUT_RESPUESTA_RAPIDA if self.es_mensaje_rapido else ANCHO_INPUT_RESPUESTA_PERSONALIZADA,
            height=38,
            wrap="word",
            font=("Consolas", 11),
            fg_color=("#FFFFFF", "#2B2B2B"),
            border_width=1,
            corner_radius=8,
            activate_scrollbars=True,
            undo=False
        )
        self.reply_entry.grid(
            row=row,
            column=column,
            columnspan=columnspan,
            sticky="ew",
            padx=(10 if self.es_mensaje_rapido else PADDING_INTERNO_REPLY, SEPARACION_INPUT_BOTON),
            pady=(4 if self.es_mensaje_rapido else 0, 10 if self.es_mensaje_rapido else PADDING_INTERNO_REPLY)
        )
        self.reply_entry.focus_set()

        self.send_button = ctk.CTkButton(
            self.reply_frame,
            text="Enviar",
            width=ANCHO_BOTON_ENVIAR,
            height=30,
            state="disabled"
        )
        self.send_button.grid(
            row=row,
            column=button_column,
            padx=(0, 10 if self.es_mensaje_rapido else PADDING_INTERNO_REPLY),
            pady=(4 if self.es_mensaje_rapido else 0, 10 if self.es_mensaje_rapido else PADDING_INTERNO_REPLY),
            # padx=(0, 10 if self.es_mensaje_rapido else 0),
            # pady=(4 if self.es_mensaje_rapido else 0, 10 if self.es_mensaje_rapido else 0),
            sticky="e"
        )

    def _configurar_controles_respuesta(self):
        self.reply_entry.bind("<KeyRelease>", self._actualizar_estado_enviar)
        self.reply_entry.bind("<Return>", self._on_reply_return)
        self.reply_entry.bind("<Shift-Return>", self._on_reply_shift_return)
        self.send_button.bind("<ButtonPress-1>", self._on_send_press)
        self.send_button.bind("<ButtonRelease-1>", self._on_send_release)
        self.send_button.bind("<B1-Motion>", self._stop_interactive_drag)
        self.send_button.bind("<Leave>", self._on_send_leave)
        self.reply_entry.bind("<ButtonPress-1>", self._stop_text_input_drag)
        self.reply_entry.bind("<B1-Motion>", self._stop_text_input_drag)
        self.reply_entry.bind("<ButtonRelease-1>", self._stop_text_input_drag)
        try:
            self.reply_entry._textbox.bind("<KeyRelease>", self._actualizar_estado_enviar)
            self.reply_entry._textbox.bind("<Return>", self._on_reply_return)
            self.reply_entry._textbox.bind("<Shift-Return>", self._on_reply_shift_return)
            self.reply_entry._textbox.bind("<ButtonPress-1>", self._stop_text_input_drag)
            self.reply_entry._textbox.bind("<B1-Motion>", self._stop_text_input_drag)
            self.reply_entry._textbox.bind("<ButtonRelease-1>", self._stop_text_input_drag)
        except Exception:
            pass
        self._actualizar_estado_enviar()

    def _on_message_text_key(self, event=None):
        if event is None:
            return "break"

        if event.state & 0x4:
            return None

        if event.keysym in {"BackSpace", "Delete", "Return", "Tab", "Escape"}:
            return "break"

        if event.keysym in {"Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next"}:
            return None

        return "break"

    def _on_reply_return(self, event=None):
        if self._closing:
            return "break"

        self.enviar_respuesta()
        return "break"

    def _on_reply_shift_return(self, event=None):
        if self.reply_entry is None:
            return "break"

        self.reply_entry.insert("insert", "\n")
        self.reply_entry.see("end")
        self._actualizar_estado_enviar()
        return "break"

    def _on_copy_press(self, event):
        if self._closing:
            return "break"
        # Inicia contador de presión
        try:
            self._copy_press_start_ms = int(time.time() * 1000)
        except Exception:
            self._copy_press_start_ms = None

        self._copy_btn_pressed = True
        self.dragging = False
        self._start_recarga_updater()
        return "break"

    def _on_copy_release(self, event):
        # Determina duración de la presión en ms
        duration_ms = 0
        try:
            if self._copy_press_start_ms is not None:
                duration_ms = int(time.time() * 1000) - int(self._copy_press_start_ms)
        except Exception:
            duration_ms = 0

        # Guarda la duración para que `copiar_mensaje` la utilice
        self._last_copy_press_duration_ms = max(0, int(duration_ms))

        if self._copy_btn_pressed and self._event_inside_widget(event, self.copy_button):
            self.copiar_mensaje()

        self._stop_recarga_updater()
        self._schedule_recarga_hide()
        self._copy_btn_pressed = False
        self._copy_press_start_ms = None
        return "break"

    def _on_copy_leave(self, event):
        # Cancelar la cuenta si el cursor sale del botón
        self._copy_btn_pressed = False
        self._copy_press_start_ms = None
        self._stop_recarga_updater()
        self._schedule_recarga_hide()
        return "break"

    def copiar_mensaje(self):
        texto = self.mensaje_texto or ""
        if not texto:
            return

        try:
            self.clipboard_clear()
            self.clipboard_append(texto)
        except Exception:
            pass

        if self.copy_button is None:
            return

        def _mostrar_checkmark():
            try:
                self.copy_button.configure(
                    text=ICONO_COPIADO,
                    width=ANCHO_BOTON_COPIAR,
                    height=ALTO_BOTON_COPIAR
                )
                self.after(
                    1200,
                    lambda: self.copy_button.configure(
                        text=ICONO_COPIAR,
                        width=ANCHO_BOTON_COPIAR,
                        height=ALTO_BOTON_COPIAR
                    ) if self.copy_button is not None else None
                )
            except Exception:
                pass

        try:
            icono_path = resource_path(os.path.join("res", "clipboard.png"))
            # Calcular píxeles extra basados en la duración de la presión
            duracion = getattr(self, "_last_copy_press_duration_ms", 0) or 0
            extra_px = 0
            try:
                if duracion > RECARGA_SALTO_THRESHOLD_MS:
                    extra_ms = duracion - RECARGA_SALTO_THRESHOLD_MS
                    extra_px = int(extra_ms // RECARGA_SALTO_RATE_MS_PER_PX)
                    if extra_px > RECARGA_SALTO_MAX_EXTRA_PX:
                        extra_px = RECARGA_SALTO_MAX_EXTRA_PX
            except Exception:
                extra_px = 0

            def _on_anim_complete():
                # resetear contador tras completar la animación
                try:
                    self._last_copy_press_duration_ms = 0
                except Exception:
                    pass
                self._hide_recarga_indicator()
                _mostrar_checkmark()

            animacion = AnimacionSaltoMoneda(
                self.copy_button,
                icono_path,
                extra_force_px=extra_px,
                on_complete=_on_anim_complete
            )
            animacion.iniciar()
        except Exception:
            _mostrar_checkmark()
            try:
                self._last_copy_press_duration_ms = 0
            except Exception:
                pass

    def _bind_reply_button_events(self):
        self.reply_button.bind("<ButtonPress-1>", self._on_reply_press)
        self.reply_button.bind("<ButtonRelease-1>", self._on_reply_release)
        self.reply_button.bind("<B1-Motion>", self._stop_interactive_drag)
        self.reply_button.bind("<Leave>", self._on_reply_leave)

    def _texto_destinatarios(self):
        if not self.destinatarios:
            return "No informado"

        filas = [
            (
                self._obtener_alias_destinatario(hostname),
                hostname
            )
            for hostname in self.destinatarios
        ]
        ancho_alias = max(len(alias) for alias, _ in filas)
        return "\n".join(
            f"{alias:<{ancho_alias}}  {hostname}"
            for alias, hostname in filas
        )

    def _obtener_alias_destinatario(self, hostname):
        clave = str(hostname).strip().upper()
        alias = self._destinatario_aliases.get(clave)
        if alias and str(alias).strip().upper() != clave:
            return str(alias).strip()

        try:
            resolver = getattr(self.master, "obtener_alias_equipo", None)
            if callable(resolver):
                alias = resolver(hostname)
                if alias and str(alias).strip().upper() != clave:
                    return str(alias).strip()
        except Exception:
            pass

        return str(hostname).strip()

    def _crear_acciones_respuesta(self, x, y, width):
        self.reply_button = ctk.CTkButton(self.main, text="Responder", width=width, height=30)
        self.reply_button.place(x=x, y=y)
        self._bind_reply_button_events()
        self.reply_menu_button = ctk.CTkButton(
            self.main,
            text="▼",
            width=30,
            height=30,
            fg_color=self.reply_button.cget("fg_color"),
            hover_color=self.reply_button.cget("hover_color")
        )
        self.reply_menu_button.place(x=x + width - 1, y=y)
        self.reply_menu_button.configure(command=self._abrir_menu_acciones)
        self.reply_menu_button.lift()

    def _abrir_menu_acciones(self):
        if self._reply_menu is not None:
            try:
                self._reply_menu.unpost()
            except Exception:
                pass
            self._reply_menu = None

        menu = tk.Menu(self, tearoff=0, bg="#1F2937", fg="#F8FAFC", activebackground="#374151", activeforeground="#FFFFFF")
        opciones = []
        if len(self.destinatarios) > 1:
            opciones.append("Responder a todos")
        opciones.append("Reenviar")

        for item in opciones:
            label = item
            if label == "Responder a todos":
                menu.add_command(label=label, command=lambda lbl=label: self._elegir_accion(lbl))
            else:
                menu.add_command(label=label, command=lambda lbl=label: self._elegir_accion(lbl))

        self._reply_menu = menu
        x = self.reply_menu_button.winfo_rootx()
        y = self.reply_menu_button.winfo_rooty() + self.reply_menu_button.winfo_height()
        menu.post(x, y)

    def _elegir_accion(self, accion):
        if self._reply_menu is not None:
            try:
                self._reply_menu.unpost()
            except Exception:
                pass
            self._reply_menu = None

        remitente = self.mensaje_data.get("from_hostname")
        if accion == "Responder a todos":
            self.reply_destinations = list(dict.fromkeys([remitente] + [d for d in self.destinatarios if d and d != self.mensaje_data.get("from_hostname")]))
            self.reply_is_forward = False
            self.lift()
            self.focus_force()
            self.mostrar_respuesta()
            return

        if accion == "Reenviar":
            self._abrir_selector_forward()
            return

        self.reply_destinations = [remitente] if remitente else []
        self.reply_is_forward = False
        self.mostrar_respuesta()

    def _abrir_selector_forward(self):
        candidatos = []
        for item in self.available_destinations:
            if isinstance(item, dict):
                hostname = item.get("hostname") or item.get("name")
                label = item.get("label") or hostname or ""
            else:
                hostname = item
                label = item
            if hostname and hostname != self.mensaje_data.get("from_hostname"):
                candidatos.append((hostname, label))

        if not candidatos:
            candidatos = [(self.mensaje_data.get("from_hostname"), self.mensaje_data.get("from_alias") or self.mensaje_data.get("from_hostname"))]

        selector = ctk.CTkToplevel(self)
        selector.title("Reenviar a")
        selector.geometry("300x280")
        selector.transient(self)
        selector.update_idletasks()
        popup_x = self.winfo_rootx()
        popup_y = self.winfo_rooty()
        popup_width = self.winfo_width()
        popup_height = self.winfo_height()
        selector_width = selector.winfo_width()
        selector_height = selector.winfo_height()
        selector_x = popup_x + max(0, (popup_width - selector_width) // 2)
        selector_y = popup_y + max(0, (popup_height - selector_height) // 2)
        selector.geometry(f"{selector_width}x{selector_height}+{selector_x}+{selector_y}")
        selector.lift()
        selector.focus_force()
        selector.grab_set()
        ctk.CTkLabel(selector, text="Seleccioná destinatarios").pack(pady=(14, 8))
        variables = {}
        for hostname, label in sorted(set(candidatos), key=lambda item: item[1].lower()):
            variable = ctk.BooleanVar(value=False)
            variables[hostname] = variable
            ctk.CTkCheckBox(selector, text=label, variable=variable).pack(anchor="w", padx=24, pady=2)

        def confirmar():
            destinos = [hostname for hostname, variable in variables.items() if variable.get()]
            if not destinos:
                selector.grab_release()
                selector.destroy()
                return
            self.reply_destinations = destinos
            self.reply_is_forward = True
            selector.grab_release()
            selector.destroy()
            self.mostrar_respuesta()

        ctk.CTkButton(selector, text="Continuar", command=confirmar).pack(pady=16)

    def _calcular_extra_px(self, duracion_ms):
        extra_px = 0
        try:
            if duracion_ms > RECARGA_SALTO_THRESHOLD_MS:
                extra_ms = duracion_ms - RECARGA_SALTO_THRESHOLD_MS
                extra_px = int(extra_ms // RECARGA_SALTO_RATE_MS_PER_PX)
                if extra_px > RECARGA_SALTO_MAX_EXTRA_PX:
                    extra_px = RECARGA_SALTO_MAX_EXTRA_PX
        except Exception:
            extra_px = 0
        return extra_px

    def _update_recarga_label(self):
        if not self._copy_btn_pressed:
            return

        duration_ms = 0
        try:
            if self._copy_press_start_ms is not None:
                duration_ms = int(time.time() * 1000) - int(self._copy_press_start_ms)
        except Exception:
            duration_ms = 0

        extra_px = self._calcular_extra_px(duration_ms)
        if self._recarga_indicator is not None:
            self._recarga_indicator.actualizar(extra_px)

        # Si llegamos al máximo, pinta el botón de dorado y marca el estado
        try:
            if extra_px >= RECARGA_SALTO_MAX_EXTRA_PX:
                if not getattr(self, '_copy_is_gold', False):
                    try:
                        if getattr(self, '_copy_original_fg_color', None) is None:
                            self._copy_original_fg_color = self.copy_button.cget('fg_color')
                    except Exception:
                        self._copy_original_fg_color = '#2563EB'
                    try:
                        if getattr(self, '_copy_original_hover_color', None) is None:
                            self._copy_original_hover_color = self.copy_button.cget('hover_color')
                    except Exception:
                        self._copy_original_hover_color = '#1D4ED8'
                    try:
                        self.copy_button.configure(fg_color="#D4AF37", hover_color="#D4AF37")
                    except Exception:
                        pass
                    self._copy_is_gold = True
        except Exception:
            pass

        self._recarga_update_after_id = self.after(50, self._update_recarga_label)

    def _start_recarga_updater(self):
        self._cancel_recarga_hide()
        self._stop_recarga_updater()
        self._update_recarga_label()

    def _stop_recarga_updater(self):
        if self._recarga_update_after_id is not None:
            try:
                self.after_cancel(self._recarga_update_after_id)
            except Exception:
                pass
            self._recarga_update_after_id = None

    def _cancel_recarga_hide(self):
        if self._recarga_hide_after_id is not None:
            try:
                self.after_cancel(self._recarga_hide_after_id)
            except Exception:
                pass
            self._recarga_hide_after_id = None

    def _hide_recarga_indicator(self):
        if self._recarga_indicator is not None:
            self._recarga_indicator.ocultar()

        # Restaurar color del botón si estaba dorado
        try:
            if getattr(self, '_copy_is_gold', False) and getattr(self, 'copy_button', None) is not None:
                kw = {}
                if getattr(self, '_copy_original_fg_color', None) is not None:
                    kw['fg_color'] = self._copy_original_fg_color
                if getattr(self, '_copy_original_hover_color', None) is not None:
                    kw['hover_color'] = self._copy_original_hover_color
                try:
                    if kw:
                        self.copy_button.configure(**kw)
                except Exception:
                    pass
                self._copy_is_gold = False
        except Exception:
            pass

        if self._recarga_hide_after_id is not None:
            try:
                self.after_cancel(self._recarga_hide_after_id)
            except Exception:
                pass
            self._recarga_hide_after_id = None

    def _schedule_recarga_hide(self):
        if self._recarga_hide_after_id is not None:
            try:
                self.after_cancel(self._recarga_hide_after_id)
            except Exception:
                pass
            self._recarga_hide_after_id = None

        self._recarga_hide_after_id = self.after(2000, self._hide_recarga_indicator)

    def _actualizar_estado_enviar(self, *args):
        if self.send_button is None or self.reply_entry is None:
            return

        texto = self.reply_entry.get("1.0", "end-1c").strip()
        estado = "normal" if texto else "disabled"
        self.send_button.configure(state=estado)

    def _mostrar_error_respuesta_vacia(self):
        if self.reply_frame is None:
            return

        if self.reply_error_label is None:
            self.reply_error_label = ctk.CTkLabel(
                self.reply_frame,
                text="Ingresa un mensaje",
                font=("Consolas", 10, "bold"),
                text_color="#FFFFFF",
                fg_color="#D33",
                corner_radius=6
            )

        self.reply_error_label.place(relx=1.0, rely=0.0, x=-8, y=-6, anchor="ne")
        self.reply_error_label.lift()

        if self.reply_error_after_id is not None:
            try:
                self.after_cancel(self.reply_error_after_id)
            except Exception:
                pass

        self.reply_error_after_id = self.after(1600, self._ocultar_error_respuesta_vacia)

    def _ocultar_error_respuesta_vacia(self):
        self.reply_error_after_id = None
        if self.reply_error_label is not None:
            self.reply_error_label.place_forget()

    def _on_middle_click(self, event=None):
        if self._closing:
            return "break"
        self.close_animation()
        return "break"

    def _on_close_press(self, event):
        if self._closing:
            return "break"

        self._close_btn_pressed = True
        self.dragging = False
        return "break"

    def _on_close_release(self, event):
        if self._close_btn_pressed and self._event_inside_widget(event, self.close_btn):
            self.close_animation()
        self._close_btn_pressed = False
        return "break"

    def _on_close_leave(self, event):
        self._close_btn_pressed = False
        return "break"

    def _on_send_press(self, event):
        if self._closing:
            return "break"

        if not self._respuesta_tiene_texto():
            self._mostrar_error_respuesta_vacia()
            return "break"

        self._send_btn_pressed = True
        self.dragging = False
        return "break"

    def _on_send_release(self, event):
        if self._send_btn_pressed and self._event_inside_widget(event, self.send_button):
            self.enviar_respuesta()
        self._send_btn_pressed = False
        return "break"

    def _on_send_leave(self, event):
        self._send_btn_pressed = False
        return "break"

    def _on_reply_press(self, event):
        if self._closing:
            return "break"

        try:
            if self.reply_button.cget("state") == "disabled":
                return "break"
        except Exception:
            pass

        self._reply_btn_pressed = True
        self.dragging = False
        return "break"

    def _on_reply_release(self, event):
        if self._reply_btn_pressed and self._event_inside_widget(event, self.reply_button):
            self.mostrar_respuesta()
        self._reply_btn_pressed = False
        return "break"

    def _on_reply_leave(self, event):
        self._reply_btn_pressed = False
        return "break"

    def _stop_interactive_drag(self, event=None):
        self.dragging = False
        return "break"

    def _stop_text_input_drag(self, event=None):
        self.dragging = False

    def enviar_respuesta(self):
        if self.reply_entry is None or self.on_reply is None:
            return

        texto = self.reply_entry.get("1.0", "end-1c").strip()
        if not texto:
            self._mostrar_error_respuesta_vacia()
            return

        self.on_reply(self.mensaje_data, texto, self.reply_destinations, self.reply_is_forward)
        self.close_animation()

    def _respuesta_tiene_texto(self):
        if self.reply_entry is None:
            return False

        return bool(self.reply_entry.get("1.0", "end-1c").strip())

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
        if self._closing or self._is_interactive_event(event):
            self.dragging = False
            return "break"

        self.dragging = True
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.drag_window_x = self.current_x
        self.drag_window_y = self.current_y

    def _is_interactive_event(self, event):
        ignored_widgets = [
            getattr(self, "close_btn", None),
            getattr(self, "send_button", None),
            getattr(self, "reply_button", None),
            getattr(self, "reply_entry", None),
            getattr(self, "reply_preview", None),
            getattr(self, "message_reply_preview", None),
            getattr(self, "msg_text_widget", None),
            getattr(self, "copy_button", None),
            getattr(self, "destinatarios_label", None)
        ]

        return any(
            widget is not None and self._event_targets_widget(event, widget)
            for widget in ignored_widgets
        )

    def _event_targets_widget(self, event, widget):
        event_widget = getattr(event, "widget", None)
        while event_widget is not None:
            if event_widget is widget:
                return True
            event_widget = getattr(event_widget, "master", None)

        return self._event_inside_widget(event, widget)

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

    def do_drag(self, event):
        if self._closing or self._is_interactive_event(event):
            self.dragging = False
            return "break"

        if not self.dragging:
            return None

        new_x = self.drag_window_x + (event.x_root - self.drag_start_x)
        new_y = self.drag_window_y + (event.y_root - self.drag_start_y)

        self.current_x = new_x
        self.target_x = new_x
        self.current_y = new_y
        self.target_y = new_y
        self.geometry(f"{self.width}x{self.height}+{new_x}+{new_y}")

    def end_drag(self, event):
        if self._is_interactive_event(event):
            self.dragging = False
            return "break"

        if not self.dragging:
            return None

        self.dragging = False
        self.current_x = self.target_x
        self.current_y = self.target_y
        self.target_x = self.current_x
        self.target_y = self.current_y
        ToastPopup.ultima_posicion = (int(self.current_x), int(self.current_y))
        ToastPopup.contador_posicion = 0

    def fade_in(self):
        if self._closing:
            self._fade_after_id = None
            return

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
            self._fade_after_id = self.after(16, self.fade_in)
        else:
            self._fade_after_id = None

    def close_animation(self):
        if self._close_after_id is not None:
            return

        self._closing = True
        self.dragging = False
        self._cerrar_imagen_submenu()
        self._cancel_after("_fade_after_id")
        self._animate_close()

    def _cerrar_imagen_submenu(self):
        popup = getattr(self, "quick_reply_image_popup", None)
        if popup is None:
            return

        try:
            popup.close_animation()
        except Exception:
            try:
                popup.destroy()
            except Exception:
                pass
        self.quick_reply_image_popup = None

    def _animate_close(self):
        self._close_after_id = None
        alpha = self.attributes("-alpha")

        if alpha > 0.02:
            alpha -= 0.06
            self.attributes("-alpha", alpha)

            self.current_y += 2

            self.geometry(
                f"{self.width}x{self.height}+"
                f"{int(self.current_x)}+{int(self.current_y)}"
            )
            self._close_after_id = self.after(16, self._animate_close)
        else:
            self.destroy()

    def _cancel_after(self, attr_name):
        after_id = getattr(self, attr_name, None)
        if after_id is None:
            return

        try:
            self.after_cancel(after_id)
        except Exception:
            pass

    def destroy(self):
        self._stop_recarga_updater()
        self._hide_recarga_indicator()
        self._cerrar_imagen_submenu()
        try:
            super().destroy()
        except Exception:
            pass
