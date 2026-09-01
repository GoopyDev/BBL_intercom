import math
import tkinter as tk
from PIL import Image, ImageOps, ImageTk

OSCILACION_HORIZONTAL = 4
ALTURA_SALTO_PX = 130
VELOCIDAD_CUADRO_MS = 15
DURACION_TOTAL_MS = 500
PROPORCION_SUBIDA = 0.45
GRAVEDAD = 2.2
COLOR_CLAVE_TRANSPARENTE = "#ab34cd"
_CACHE_IMAGENES = {}
ANCHO_AJUSTE = 10;
ALTO_AJUSTE = 0;
DESPLAZAMIENTO_X = 86 # Posición X
MARGEN_SUPERIOR_OVERLAY = 550  # aire extra arriba del punto más alto del salto
MARGEN_LATERAL_OVERLAY = 162

# Recarga de salto: configuración para la característica que añade altura
# Si el usuario mantiene presionado el botón más allá de `RECARGA_SALTO_THRESHOLD_MS`,
# se sumará 1px por cada `RECARGA_SALTO_RATE_MS_PER_PX` milisegundos, hasta el máximo.
RECARGA_SALTO_THRESHOLD_MS = 800  # ms (ajustable)
RECARGA_SALTO_RATE_MS_PER_PX = 10  # ms por píxel adicional
RECARGA_SALTO_MAX_EXTRA_PX = 500   # máximo píxeles adicionales

class AnimacionSaltoMoneda:
    """Reproduce una animación de moneda que salta y gira sobre un overlay transparente."""

    def __init__(self, widget, icon_path, extra_force_px=0, on_complete=None):
        self.widget = widget
        self.icon_path = icon_path
        self.on_complete = on_complete
        # fuerza extra en píxeles aplicada a la altura del salto (por la "Recarga de salto")
        try:
            self._extra_force_px = min(int(extra_force_px), RECARGA_SALTO_MAX_EXTRA_PX)
        except Exception:
            self._extra_force_px = 0
        self._overlay = None
        self._label = None
        self._frame_id = None
        self._paso = 0
        self._total_frames = max(1, int(DURACION_TOTAL_MS // VELOCIDAD_CUADRO_MS))
        self._icono_base = self._cargar_icono_cache(icon_path)

    @classmethod
    def _cargar_icono_cache(cls, icon_path):
        if icon_path not in _CACHE_IMAGENES:
            with Image.open(icon_path) as imagen:
                imagen = imagen.convert("RGBA")
                _CACHE_IMAGENES[icon_path] = imagen.copy()
        return _CACHE_IMAGENES[icon_path]

    def iniciar(self):
        if self.widget is None or not self.widget.winfo_exists():
            return

        self._crear_overlay()
        self._animar_frame()

    def _crear_overlay(self):
        ventana_padre = self.widget.winfo_toplevel()
        self._overlay = tk.Toplevel(ventana_padre)
        self._overlay.withdraw()
        self._overlay.overrideredirect(True)
        self._overlay.attributes("-topmost", True)
        self._overlay.configure(bg=COLOR_CLAVE_TRANSPARENTE)

        try:
            self._overlay.wm_attributes("-transparentcolor", COLOR_CLAVE_TRANSPARENTE)
        except Exception:
            pass

        ancho = max(self.widget.winfo_width() + MARGEN_LATERAL_OVERLAY, 48)
        alto_extra_arriba = ALTURA_SALTO_PX + RECARGA_SALTO_MAX_EXTRA_PX + MARGEN_SUPERIOR_OVERLAY
        alto = self.widget.winfo_height() + alto_extra_arriba
        x = self.widget.winfo_rootx() - (MARGEN_LATERAL_OVERLAY // 2)
        y = self.widget.winfo_rooty() - alto_extra_arriba

        self._overlay.geometry(f"{ancho}x{alto}+{x}+{y}")

        self._baseline_y = alto_extra_arriba # posicion (altura=0) alineada con el borde superior del boton

        self._label = tk.Label(
            self._overlay,
            bg=COLOR_CLAVE_TRANSPARENTE,
            bd=0,
            highlightthickness=0
        )
        self._label.place(x=0, y=0)

        self._overlay.deiconify()

    def _animar_frame(self):
        if self._overlay is None or not self._overlay.winfo_exists():
            return

        if self._paso >= self._total_frames:
            self._finalizar()
            return

        progreso = self._paso / max(1, self._total_frames - 1)
        altura = self._calcular_altura(progreso)

        foto = self._renderizar_foto(progreso)
        ancho_foto, alto_foto = foto.width() + ANCHO_AJUSTE, foto.height() + ALTO_AJUSTE
        x = max(0, (self.widget.winfo_width() - ancho_foto) // 2 + DESPLAZAMIENTO_X)
        # Aplica la altura base más la fuerza extra (si la hubiera)
        salto_total = ALTURA_SALTO_PX + getattr(self, "_extra_force_px", 0)
        y = int(self._baseline_y - (altura * salto_total))

        self._label.configure(image=foto)
        self._label.image = foto
        self._label.place(x=x, y=y)


        self._paso += 1
        self._frame_id = self._overlay.after(VELOCIDAD_CUADRO_MS, self._animar_frame)

    def _calcular_altura(self, progreso):
        if progreso < PROPORCION_SUBIDA:
            t = progreso / PROPORCION_SUBIDA
            return 1 - (1 - t) ** 3

        t = (progreso - PROPORCION_SUBIDA) / (1 - PROPORCION_SUBIDA)
        return 1 - (t ** GRAVEDAD)

    def _renderizar_foto(self, progreso):
        base_w, base_h = self._icono_base.size

        # La moneda empieza y termina de frente.
        # Durante el salto se comprime horizontalmente.
        factor_ancho = abs(
            math.cos(progreso * math.pi * OSCILACION_HORIZONTAL)
        )

        # Evita que llegue literalmente a 1 píxel de ancho.
        factor_ancho = max(0.08, factor_ancho)

        ancho = max(1, int(base_w * factor_ancho))
        alto = base_h

        icono_ajustado = self._icono_base.resize(
            (ancho, alto),
            Image.Resampling.BICUBIC
        )

        if int(progreso * OSCILACION_HORIZONTAL) % 2 == 1:
            icono_ajustado = ImageOps.mirror(icono_ajustado)

        lienzo = Image.new(
            "RGBA",
            (base_w, base_h),
            (0, 0, 0, 0)
        )

        offset_x = (base_w - ancho) // 2

        lienzo.paste(
            icono_ajustado,
            (offset_x, 0),
            icono_ajustado
        )

        fondo_clave = Image.new(
            "RGBA",
            lienzo.size,
            self._color_clave_rgba()
        )

        fondo_clave.alpha_composite(lienzo)

        return ImageTk.PhotoImage(fondo_clave)

    def _color_clave_rgba(self):
        color = COLOR_CLAVE_TRANSPARENTE.lstrip("#")
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)) + (255,)

    def _finalizar(self):
        if self._frame_id is not None:
            try:
                self._overlay.after_cancel(self._frame_id)
            except Exception:
                pass
            self._frame_id = None

        if self._overlay is not None and self._overlay.winfo_exists():
            self._overlay.destroy()

        if self.on_complete is not None:
            try:
                self.on_complete()
            except Exception:
                pass


class IndicadorRecargaSalto:
    """Indicador flotante de recarga que aparece junto al botón Copiar."""

    def __init__(self, widget):
        self.widget = widget
        self._overlay = None
        self._label = None
        self._visible = False
        self._crear_overlay()

    def _crear_overlay(self):
        if self.widget is None or not self.widget.winfo_exists():
            return

        ventana_padre = self.widget.winfo_toplevel()
        self._overlay = tk.Toplevel(ventana_padre)
        self._overlay.withdraw()
        self._overlay.overrideredirect(True)
        self._overlay.attributes("-topmost", True)
        self._overlay.configure(bg=COLOR_CLAVE_TRANSPARENTE)
        try:
            self._overlay.wm_attributes("-transparentcolor", COLOR_CLAVE_TRANSPARENTE)
        except Exception:
            pass

        self._label = tk.Label(
            self._overlay,
            text="",
            font=("Consolas", 10, "bold"),
            fg="#00FF00",
            bg=COLOR_CLAVE_TRANSPARENTE,
            bd=0,
            highlightthickness=0
        )
        self._label.place(x=0, y=0)

    def actualizar(self, extra_px):
        if self.widget is None or not self.widget.winfo_exists():
            return

        if extra_px <= 0:
            self.ocultar()
            return

        texto = f"+{extra_px}"
        if self._label is not None:
            self._label.configure(text=texto)
            self._overlay.update_idletasks()

            widget_x = self.widget.winfo_rootx()
            widget_y = self.widget.winfo_rooty()
            widget_w = self.widget.winfo_width()
            widget_h = self.widget.winfo_height()
            label_width = self._label.winfo_reqwidth()
            label_height = self._label.winfo_reqheight()

            overlay_x = widget_x + max(0, (widget_w - label_width) // 2)
            overlay_y = widget_y + widget_h + 6
            self._overlay.geometry(f"{label_width}x{label_height}+{overlay_x}+{overlay_y}")
            self.mostrar()

    def mostrar(self):
        if self._overlay is None or not self.widget.winfo_exists():
            return

        self._overlay.deiconify()
        self._overlay.lift()
        self._visible = True

    def ocultar(self):
        if self._overlay is None or not self._overlay.winfo_exists():
            return

        self._overlay.withdraw()
        self._visible = False

    def destruir(self):
        if self._overlay is None:
            return

        try:
            if self._overlay.winfo_exists():
                self._overlay.destroy()
        except Exception:
            pass
        self._overlay = None
        self._label = None
        self._visible = False
