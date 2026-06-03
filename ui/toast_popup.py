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

    # indice actual
    idx = ROTACION_FONDOS.get(mensaje, 0)

    fondo = fondos[idx]

    # avanzar rotacion
    idx += 1

    if idx >= len(fondos):
        idx = 0

    ROTACION_FONDOS[mensaje] = idx

    return fondo


class ToastPopup(ctk.CTkToplevel):
    """Notificacion flotante con el mismo aspecto y animaciones originales."""
    ultima_posicion = None
    contador_posicion = 0

    def __init__(self, master, remitente, mensaje):
        super().__init__(master)

        # TAMAÑO DE LAS NOTIFICACIONES
        # ============================
        self.width = 360
        self.height = 200
        # ============================

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)

        # Posicion esquina inferior derecha
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

        # Frame principal
        self.main = ctk.CTkFrame(
            self,
            # corner_radius=18,
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
        self.overlay = None
        self.scroll_frame = None
        self.es_mensaje_rapido = mensaje in MENSAJES_RAPIDOS

        # FONDO DINAMICO
        fondo = obtener_fondo_popup(mensaje)

        if fondo:
            try:
                fondo_path = resource_path(os.path.join("res", fondo))

                self.bg_pil_image = Image.open(fondo_path)

                # Guardamos la imagen en self para evitar que Python la libere
                # mientras el popup sigue visible.
                self.bg_image = ctk.CTkImage(
                    light_image=self.bg_pil_image,
                    dark_image=self.bg_pil_image,
                    size=(self.width, self.height)
                )

                self.bg_label = ctk.CTkLabel(self.main, image=self.bg_image, text="", width=self.width, height=self.height)

                self.bg_label.place(x=0, y=0)
                self._bind_drag(self.bg_label)

            except Exception as e:
                print(f"Error cargando fondo: {e}")

        if self.es_mensaje_rapido:
            self._crear_contenido_rapido(remitente, mensaje)
        else:
            self._crear_contenido_personalizado(remitente, mensaje)

        # Boton cerrar
        self.close_btn = ctk.CTkButton(
            self.main,
            text="✕",
            text_color=COLOR_POPUP_TEXTO,
            width=28,
            height=28,
            fg_color="transparent",
            bg_color="transparent",
            hover_color="#D33",
            command=self.close_animation
        )
        self.close_btn.place(x=325, y=6)

        # Orden final
        if self.bg_label is not None:
            self.bg_label.lift()
        self.title_label.lift()
        if self.scroll_frame is not None:
            self.scroll_frame.lift()
        self.msg_label.lift()
        self.close_btn.lift()

        self.fade_in()

    def _crear_contenido_rapido(self, remitente, mensaje):
        """Mantiene las posiciones originales para mensajes predefinidos."""
        # Remitente
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

        # Mensaje
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

    def _crear_contenido_personalizado(self, remitente, mensaje):
        """Usa alias arriba y area con scroll para mensajes personalizados con contenedor intermediario."""
        # 1. Remitente (Igual que antes)
        self.title_label = ctk.CTkLabel(
            self.main,
            text=remitente,
            font=("Consolas", 14, "bold"),
            anchor="w",
            width=275,
            text_color=COLOR_POPUP_TEXTO
        )
        self.title_label.place(x=18, y=14)
        self._bind_drag(self.title_label)

        # 2. CONTENEDOR INTERMEDIARIO (Frame normal)
        # Este frame va a actuar como un "ancla" invisible con el tamaño exacto que querés.
        self.contenedor_limite = ctk.CTkFrame(
            self.main,
            width=320,
            height=130, # <--- Modificá este alto exacto para que encaje perfecto en tu popup
            # corner_radius=10,
            fg_color=COLOR_POPUP_CONTENEDOR
            # fg_color="transparent" # Lo hacemos invisible para que no rompa tu estética
        )
        # Lo posicionamos a 48px del techo. De acá no se va a mover ni va a crecer.
        self.contenedor_limite.place(x=18, y=48)
        
        # Evitamos que el frame se achique o se estire por culpa de lo que metamos dentro
        self.contenedor_limite.pack_propagate(False)

        # 3. EL SCROLLABLE FRAME (Hijo del contenedor intermediario)
        # Ya no necesita width ni height fijos en el constructor porque va a rellenar al padre.
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.contenedor_limite, # <--- Ojo acá: su padre ahora es el contenedor
            # corner_radius=10,
            fg_color="transparent"
        )
        # Le decimos que llene el 100% del contenedor intermediario
        self.scroll_frame.pack(fill="both", expand=True)

        # 4. EL TEXTO DEL MENSAJE (Hijo del scroll_frame)
        self.msg_label = ctk.CTkLabel(
            self.scroll_frame,
            text=mensaje,
            font=("Consolas", 13),
            justify="left",
            wraplength=295, # Un toque más chico que 300 para que la barra de scroll no pise el texto
            anchor="nw",
            text_color=COLOR_POPUP_TEXTO
        )
        self.msg_label.pack(fill="x", expand=True, padx=(0, 10), pady=0)

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

            # movimiento hacia arriba
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

            # baja suavemente
            self.current_y += 3

            # pequeño zoom
            self.width -= 1
            self.height -= 1

            self.geometry(
                f"{self.width}x{self.height}+"
                f"{int(self.current_x)}+{int(self.current_y)}"
            )

            self.after(16, self.close_animation)

        else:
            self.destroy()
