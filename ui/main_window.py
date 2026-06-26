import ctypes
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageOps

from config.constants import APP_ICON, APP_ID, BOTONES_PRESET, TEMAS_PREDEFINIDOS
from services.message_service import enviar_mensaje, es_destino_valido, obtener_destinos, revisar_mensajes_pendientes
from services.observer_service import detener_observer, iniciar_observer
from services.profile_service import actualizar_profile_equipo, obtener_alias_equipo
from ui.toast_popup import ToastPopup
from utils.resources import resource_path


# Esto le dice a Windows que trate a este proceso como una aplicacion con identidad propia.
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except Exception:
    pass


class ITMessenger(ctk.CTk):
    """Ventana principal de la aplicacion CustomTkinter."""
    def __init__(self):
        super().__init__()
        self.hostname = socket.gethostname().upper()
        self.ruta_config = os.path.join(os.environ["APPDATA"], "IT_Messenger_Config.json")
        self.ruta_runtime = os.path.join(os.environ["APPDATA"], "BBL_Chat_Runtime.json")
        self.ruta_teams = ""
        self.alias = ""
        self.check_vars = {}
        self.observer = None
        self.modo_oscuro_var = ctk.BooleanVar(value=True)
        self.confirmacion_envio_after_id = None
        self.banner_top_pil_image = None
        self.banner_top_image = None
        self.banner_top_label = None
        self.btn_reiniciar = None
        self.btn_enviar_personalizado = None
        self.tema_tipo = "predefinido"
        self.tema_id = "darkclassic"
        self.temas = []
        self.tema_por_display = {}
        self.tema_actual = None
        self.tema_var = ctk.StringVar(value="")
        self.botones_rapidos = []
        self.boton_rapido_presionado = None
        self.startup_enabled_var = ctk.BooleanVar(value=False)
        self.reinicio_delay_ms = 3000
        self.cierre_reinicio_delay_ms = 750
        self.reinicio_modal = None
        self.reinicio_bg_image = None
        self.reinicio_bg_pil_image = None
        self.ruta_log_reinicio = os.path.join(os.path.dirname(self.ruta_config), "IT_Messenger_Config.log")
        self.ventana_config = {}
        self.ultima_geometria_normal = {
            "x": 100,
            "y": 100,
            "width": 850,
            "height": 850
        }

        self.guardar_ruta_ejecucion_actual()
        self.cargar_config()
        self.setup_ui()

    def obtener_ruta_ejecucion_actual(self):
        """Devuelve la ruta estable desde la que se debe relanzar la app."""
        if getattr(sys, "frozen", False):
            candidatos = [sys.executable, sys.argv[0]]
        else:
            candidatos = [os.path.abspath(sys.argv[0])]

        for candidato in candidatos:
            if not candidato:
                continue

            ruta = os.path.abspath(candidato)
            if os.path.isfile(ruta) and not self.es_ruta_temporal(ruta):
                return ruta

        return ""

    def es_ruta_temporal(self, ruta):
        """Evita persistir rutas temporales usadas por PyInstaller onefile."""
        try:
            ruta_abs = os.path.abspath(ruta)
            temp_abs = os.path.abspath(os.environ.get("TEMP") or os.environ.get("TMP") or "")
            if temp_abs and os.path.commonpath([ruta_abs, temp_abs]) == temp_abs:
                return True
        except Exception:
            pass

        partes = os.path.abspath(ruta).upper().split(os.sep)
        return any(parte.startswith("_MEI") for parte in partes)

    def guardar_ruta_ejecucion_actual(self):
        """Persiste el ejecutable real para reinicios fuera del runtime temporal."""
        ruta_ejecucion = self.obtener_ruta_ejecucion_actual()
        if not ruta_ejecucion:
            return

        try:
            with open(self.ruta_runtime, "w", encoding="utf-8") as f:
                json.dump({
                    "executable_path": ruta_ejecucion
                }, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"No se pudo guardar la ruta de ejecucion: {e}")

    def obtener_ruta_ejecucion_guardada(self):
        """Lee la ruta persistida y valida que siga existiendo."""
        try:
            with open(self.ruta_runtime, "r", encoding="utf-8") as f:
                data = json.load(f)

            ruta = os.path.abspath(data.get("executable_path") or "")
            if os.path.isfile(ruta) and not self.es_ruta_temporal(ruta):
                return ruta
        except Exception:
            pass

        return self.obtener_ruta_ejecucion_actual()

    def cargar_config(self):
        """Carga la configuracion local y prepara el equipo si ya estaba registrado."""
        if os.path.exists(self.ruta_config):
            with open(self.ruta_config, "r") as f:
                data = json.load(f)
                self.ruta_teams = data.get("ruta")
                self.alias = data.get("alias") or self.hostname
                self.modo_oscuro_var.set(data.get("modo_oscuro", self.modo_oscuro_var.get()))
                self.startup_enabled_var.set(data.get("startup_enabled", self.startup_enabled_var.get()))
                tema = data.get("tema", {})
                if isinstance(tema, dict):
                    self.tema_tipo = tema.get("tipo", self.tema_tipo)
                    self.tema_id = tema.get("id", self.tema_id)
                ventana = data.get("ventana", {})
                if isinstance(ventana, dict):
                    self.ventana_config = ventana
            self.actualizar_profile_equipo()
            self.iniciar_escucha()

    def setup_ui(self):
        """Configura la ventana y decide entre registro o pantalla principal."""
        self.title(f"IT Messenger - {self.hostname}")
        self.restaurar_geometria_ventana()
        self.aplicar_modo_apariencia()
        self.aplicar_icono()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind("<Configure>", self.actualizar_geometria_ventana)

        if not self.ruta_teams:
            self.mostrar_registro()
        else:
            self.mostrar_principal()

    def aplicar_icono(self):
        """Aplica el icono de la app manteniendo compatibilidad con PyInstaller."""
        try:
            self.iconbitmap(resource_path(APP_ICON))
        except Exception as e:
            print(f"No se pudo cargar el icono de la aplicacion: {e}")

    def obtener_monitores(self):
        """Devuelve bounds/workarea de los monitores actuales usando la API de Windows."""
        monitores = []

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

            def rect_a_tuple(rect):
                return (rect.left, rect.top, rect.right, rect.bottom)

            def callback(hmonitor, hdc, rect, data):
                info = MONITORINFO()
                info.cbSize = ctypes.sizeof(MONITORINFO)
                if ctypes.windll.user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
                    monitores.append({
                        "bounds": rect_a_tuple(info.rcMonitor),
                        "work": rect_a_tuple(info.rcWork),
                        "primary": bool(info.dwFlags & 1)
                    })
                return True

            monitor_enum_proc = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.POINTER(RECT),
                ctypes.c_void_p
            )
            ctypes.windll.user32.EnumDisplayMonitors(0, 0, monitor_enum_proc(callback), 0)
        except Exception:
            monitores = []

        if not monitores:
            monitores.append({
                "bounds": (0, 0, self.winfo_screenwidth(), self.winfo_screenheight()),
                "work": (0, 0, self.winfo_screenwidth(), self.winfo_screenheight()),
                "primary": True
            })

        return monitores

    def obtener_monitor_principal(self, monitores):
        for monitor in monitores:
            if monitor.get("primary"):
                return monitor
        return monitores[0]

    def obtener_monitor_de_geometria(self, x, y, width, height, monitores):
        mejor_monitor = None
        mejor_area = 0

        for monitor in monitores:
            left, top, right, bottom = monitor["bounds"]
            inter_width = max(min(x + width, right) - max(x, left), 0)
            inter_height = max(min(y + height, bottom) - max(y, top), 0)
            area = inter_width * inter_height
            if area > mejor_area:
                mejor_area = area
                mejor_monitor = monitor

        return mejor_monitor or self.obtener_monitor_principal(monitores)

    def geometria_intersecta_monitor(self, x, y, width, height, monitor):
        left, top, right, bottom = monitor["bounds"]
        inter_width = min(x + width, right) - max(x, left)
        inter_height = min(y + height, bottom) - max(y, top)
        return inter_width >= 80 and inter_height >= 80

    def obtener_entero_config(self, cfg, clave, minimo=None):
        try:
            numero = int(cfg.get(clave))
        except (TypeError, ValueError):
            return None

        if minimo is not None and numero < minimo:
            return None

        return numero

    def ajustar_geometria_a_monitor(self, x, y, width, height, monitor):
        left, top, right, bottom = monitor["work"]
        work_width = max(right - left, 500)
        work_height = max(bottom - top, 400)

        width = min(max(width, 500), work_width)
        height = min(max(height, 400), work_height)
        x = min(max(x, left), right - width)
        y = min(max(y, top), bottom - height)

        return x, y, width, height

    def obtener_geometria_segura(self):
        cfg = self.ventana_config if isinstance(self.ventana_config, dict) else {}
        monitores = self.obtener_monitores()
        principal = self.obtener_monitor_principal(monitores)

        width = self.obtener_entero_config(cfg, "width", 500)
        height = self.obtener_entero_config(cfg, "height", 400)
        x = self.obtener_entero_config(cfg, "x")
        y = self.obtener_entero_config(cfg, "y")

        if width is None or height is None:
            width = 850
            height = 850

        if x is None or y is None:
            left, top, right, bottom = principal["work"]
            work_width = max(right - left, 500)
            work_height = max(bottom - top, 400)
            width = min(width, work_width)
            height = min(height, work_height)
            x = left + max((work_width - width) // 2, 0)
            y = top + max((work_height - height) // 2, 0)
            return x, y, width, height

        monitor_guardado = self.obtener_monitor_de_geometria(x, y, width, height, monitores)
        if self.geometria_intersecta_monitor(x, y, width, height, monitor_guardado):
            return self.ajustar_geometria_a_monitor(x, y, width, height, monitor_guardado)

        left, top, right, bottom = principal["work"]
        work_width = max(right - left, 500)
        work_height = max(bottom - top, 400)
        width = min(width, work_width)
        height = min(height, work_height)
        x = left + max((work_width - width) // 2, 0)
        y = top + max((work_height - height) // 2, 0)
        return x, y, width, height

    def restaurar_geometria_ventana(self):
        x, y, width, height = self.obtener_geometria_segura()
        self.ultima_geometria_normal = {
            "x": x,
            "y": y,
            "width": width,
            "height": height
        }
        self.geometry(f"{width}x{height}+{x}+{y}")

        if self.ventana_config.get("state") == "zoomed":
            self.after(100, lambda: self.state("zoomed"))

    def actualizar_geometria_ventana(self, event=None):
        if event is not None and event.widget is not self:
            return

        try:
            if self.state() != "normal":
                return
        except Exception:
            return

        width = self.winfo_width()
        height = self.winfo_height()
        if width < 500 or height < 400:
            return

        self.ultima_geometria_normal = {
            "x": self.winfo_x(),
            "y": self.winfo_y(),
            "width": width,
            "height": height
        }

    def obtener_config_ventana_actual(self):
        try:
            self.update_idletasks()
            estado = self.state()
        except Exception:
            estado = "normal"

        if estado == "normal":
            self.actualizar_geometria_ventana()

        geometria = dict(self.ultima_geometria_normal)

        if estado == "zoomed":
            monitores = self.obtener_monitores()
            monitor_actual = self.obtener_monitor_de_geometria(
                self.winfo_x(),
                self.winfo_y(),
                self.winfo_width(),
                self.winfo_height(),
                monitores
            )

            if not self.geometria_intersecta_monitor(
                geometria["x"],
                geometria["y"],
                geometria["width"],
                geometria["height"],
                monitor_actual
            ):
                left, top, right, bottom = monitor_actual["work"]
                work_width = max(right - left, 500)
                work_height = max(bottom - top, 400)
                width = min(geometria["width"], work_width)
                height = min(geometria["height"], work_height)
                geometria.update({
                    "x": left + max((work_width - width) // 2, 0),
                    "y": top + max((work_height - height) // 2, 0),
                    "width": width,
                    "height": height
                })

        geometria["state"] = "zoomed" if estado == "zoomed" else "normal"
        return geometria

    def mostrar_registro(self):
        """Muestra la pantalla de vinculacion inicial."""
        self.reg_frame = ctk.CTkFrame(self)
        self.reg_frame.pack(expand=True, fill="both", padx=40, pady=40)

        ctk.CTkLabel(self.reg_frame, text="Registro de Equipo", font=("Arial", 24, "bold")).pack(pady=20)
        self.ent_alias = ctk.CTkEntry(self.reg_frame, placeholder_text="Tu Alias o Nombre...", height=40)
        self.ent_alias.pack(pady=10, fill="x", padx=60)
        self.ent_alias.bind("<KeyRelease>", self.actualizar_estado_registro)
        self.ent_alias.bind("<Return>", self.vincular_con_enter)

        self.btn_vincular = ctk.CTkButton(
            self.reg_frame,
            text="Vincular Carpeta Compartida",
            command=self.vincular,
            state="disabled"
        )
        self.btn_vincular.pack(pady=10)
        self.lbl_info = ctk.CTkLabel(self.reg_frame, text="Ruta no seleccionada", text_color="gray")
        self.lbl_info.pack()

    def alias_registro_valido(self):
        return bool(self.ent_alias.get().strip())

    def actualizar_estado_registro(self, event=None):
        estado = "normal" if self.alias_registro_valido() else "disabled"
        self.btn_vincular.configure(state=estado)

    def vincular_con_enter(self, event=None):
        if self.alias_registro_valido():
            self.vincular()
        return "break"

    def vincular(self):
        """Guarda la carpeta compartida seleccionada y registra el equipo."""
        alias = self.ent_alias.get().strip()
        if not alias:
            self.lbl_info.configure(text="Completá el alias para continuar.", text_color="#D9534F")
            self.actualizar_estado_registro()
            self.ent_alias.focus_set()
            return

        ruta = filedialog.askdirectory()
        if ruta:
            os.makedirs(os.path.join(ruta, self.hostname), exist_ok=True)

            self.ruta_teams = ruta
            self.alias = alias
            self.guardar_config()
            self.actualizar_profile_equipo()
            self.iniciar_escucha()
            self.mostrar_principal()

    def guardar_config(self):
        """Guarda la configuracion local, incluida la preferencia de apariencia."""
        with open(self.ruta_config, "w") as f:
            json.dump({
                "ruta": self.ruta_teams,
                "alias": self.alias,
                "modo_oscuro": self.modo_oscuro_var.get(),
                "startup_enabled": self.startup_enabled_var.get(),
                "tema": {
                    "tipo": self.tema_tipo,
                    "id": self.tema_id
                },
                "ventana": self.obtener_config_ventana_actual()
            }, f)

    def obtener_ruta_acceso_inicio_windows(self):
        startup_dir = os.path.join(
            os.environ["APPDATA"],
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
            "Startup"
        )
        return os.path.join(startup_dir, "BBL_Chat.lnk")

    def obtener_datos_acceso_inicio_windows(self):
        if getattr(sys, "frozen", False):
            target = self.obtener_ruta_ejecucion_guardada()
            arguments = ""
            working_dir = os.path.dirname(target)
        else:
            main_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))
            target = sys.executable
            arguments = f'"{main_path}"'
            working_dir = os.path.dirname(main_path)

        return target, arguments, working_dir

    def crear_inicio_windows(self):
        """Crea el acceso directo de inicio con Windows en Startup del usuario."""
        try:
            import winshell
            from win32com.client import Dispatch

            shortcut_path = self.obtener_ruta_acceso_inicio_windows()
            os.makedirs(os.path.dirname(shortcut_path), exist_ok=True)

            target, arguments, working_dir = self.obtener_datos_acceso_inicio_windows()
            shell = Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = target
            shortcut.Arguments = arguments
            shortcut.WorkingDirectory = working_dir
            shortcut.IconLocation = target
            shortcut.save()

            winshell.shortcut(shortcut_path)
        except Exception as e:
            messagebox.showerror("Inicio con Windows", f"No se pudo crear el acceso directo de inicio:\n{e}")
            raise

    def eliminar_inicio_windows(self):
        """Elimina el acceso directo de inicio con Windows si existe."""
        try:
            shortcut_path = self.obtener_ruta_acceso_inicio_windows()
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
        except Exception as e:
            messagebox.showerror("Inicio con Windows", f"No se pudo eliminar el acceso directo de inicio:\n{e}")
            raise

    def actualizar_inicio_windows(self, estado):
        """Actualiza el acceso directo de inicio y guarda la preferencia."""
        estado_anterior = not estado

        try:
            if estado:
                self.crear_inicio_windows()
            else:
                self.eliminar_inicio_windows()

            self.startup_enabled_var.set(estado)
            self.guardar_config()
        except Exception:
            self.startup_enabled_var.set(estado_anterior)

    def sincronizar_inicio_windows(self):
        """Sincroniza el acceso directo con la preferencia guardada."""
        shortcut_path = self.obtener_ruta_acceso_inicio_windows()

        if self.startup_enabled_var.get():
            if not os.path.exists(shortcut_path):
                try:
                    self.crear_inicio_windows()
                except Exception:
                    self.startup_enabled_var.set(False)
                    self.guardar_config()
        elif os.path.exists(shortcut_path):
            try:
                self.eliminar_inicio_windows()
            except Exception:
                self.startup_enabled_var.set(True)
                self.guardar_config()

    def actualizar_profile_equipo(self):
        actualizar_profile_equipo(self.ruta_teams, self.hostname, self.alias)

    def obtener_alias_equipo(self, hostname):
        return obtener_alias_equipo(self.ruta_teams, hostname)

    def obtener_alias_config_local(self):
        """Lee el alias actual del JSON local para precargar el dialogo de edicion."""
        try:
            if os.path.exists(self.ruta_config):
                with open(self.ruta_config, "r") as f:
                    data = json.load(f)
                return data.get("alias") or self.alias or self.hostname
        except Exception:
            pass

        return self.alias or self.hostname

    def editar_alias(self):
        """Permite cambiar el alias local sin repetir el registro del equipo."""
        alias_actual = self.obtener_alias_config_local()
        dialog = ctk.CTkInputDialog(
            text="Nuevo alias:",
            title="Editar alias"
        )
        dialog.after(50, lambda: self.precargar_alias_dialog(dialog, alias_actual))
        nuevo_alias = dialog.get_input()

        if nuevo_alias is None:
            return

        nuevo_alias = nuevo_alias.strip()
        if not nuevo_alias:
            nuevo_alias = self.hostname

        self.alias = nuevo_alias
        self.btn_alias.configure(text=self.alias)
        self.guardar_config()
        self.actualizar_profile_equipo()

    def precargar_alias_dialog(self, dialog, alias_actual):
        """Completa el input del dialogo con el alias vigente."""
        try:
            dialog._entry.insert(0, alias_actual)
            dialog._entry.select_range(0, "end")
            dialog._entry.icursor("end")
        except Exception:
            pass

    def configurar_banner_top(self, header_p, banner_p, banner_base_height, banner_max_growth_ratio):
        """Carga banner_top.png como fondo del header superior."""
        try:
            banner_path = resource_path(os.path.join("res", "banner_top.png"))
            self.banner_top_pil_image = Image.open(banner_path)
            self.banner_top_label = ctk.CTkLabel(banner_p, text="")
            self.banner_top_label.place(x=0, y=0, relwidth=1, relheight=1)
            banner_p.bind(
                "<Configure>",
                lambda event: self.actualizar_banner_top(
                    header_p,
                    banner_p,
                    event.width,
                    banner_base_height,
                    banner_max_growth_ratio
                )
            )
            self.bind(
                "<Configure>",
                lambda event: self.actualizar_banner_top(
                    header_p,
                    banner_p,
                    banner_p.winfo_width(),
                    banner_base_height,
                    banner_max_growth_ratio
                ) if event.widget == self else None
            )
        except Exception as e:
            print(f"No se pudo cargar el banner superior: {e}")

    def actualizar_banner_top(self, header_p, banner_p, width, base_height, max_growth_ratio):
        """Ajusta el contenedor y la imagen del banner al tamaño actual."""
        if self.banner_top_pil_image is None or self.banner_top_label is None or width <= 1:
            return

        window_height = max(self.winfo_height(), 600)
        growth = min(max((window_height - 600) / 600, 0), 1) * max_growth_ratio
        height = int(base_height * (1 + growth))

        header_p.grid_rowconfigure(0, minsize=height)
        if banner_p.winfo_height() != height:
            banner_p.configure(height=height)

        banner_resized = ImageOps.fit(
            self.banner_top_pil_image,
            (width, height),
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5)
        )

        self.banner_top_image = ctk.CTkImage(
            light_image=banner_resized,
            dark_image=banner_resized,
            size=(width, height)
        )
        self.banner_top_label.configure(image=self.banner_top_image)

    def cargar_temas(self):
        """Carga temas predefinidos y temas personalizados desde la carpeta registrada."""
        temas = []

        for tema in TEMAS_PREDEFINIDOS:
            temas.append({
                "tipo": "predefinido",
                "id": tema["id"],
                "nombre": tema["nombre"],
                "colores": tema["colores"]
            })

        themes_dir = os.path.join(self.ruta_teams, "Themes") if self.ruta_teams else ""
        if themes_dir and os.path.isdir(themes_dir):
            for archivo in sorted(os.listdir(themes_dir)):
                if not archivo.lower().endswith(".json"):
                    continue

                ruta_tema = os.path.join(themes_dir, archivo)
                tema = self.cargar_tema_personalizado(ruta_tema)
                if tema is not None:
                    tema["tipo"] = "personalizado"
                    tema["id"] = os.path.splitext(archivo)[0]
                    temas.append(tema)

        self.temas = temas
        self.preparar_display_temas()
        self.seleccionar_tema_configurado()

    def cargar_tema_personalizado(self, ruta_tema):
        """Lee y valida un tema personalizado desde un archivo JSON."""
        try:
            with open(ruta_tema, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"No se pudo leer el tema {ruta_tema}: {e}")
            return None

        nombre = data.get("nombre")
        colores = data.get("colores")
        if not isinstance(nombre, str) or not nombre.strip() or not isinstance(colores, dict):
            print(f"Tema invalido: {ruta_tema}")
            return None

        colores_normalizados = {}
        for boton in BOTONES_PRESET:
            texto = boton["texto"]
            par = colores.get(texto, {})
            if not isinstance(par, dict):
                print(f"Tema invalido: {ruta_tema} tiene configuracion invalida en '{texto}'")
                return None

            color = par.get("color", boton["color"])
            hover = par.get("hover", boton.get("hover", boton["color"]))
            text_color = par.get("text_color", "#FFFFFF")
            if not self.es_color_hex(color) or not self.es_color_hex(hover):
                print(f"Tema invalido: {ruta_tema} tiene colores invalidos en '{texto}'")
                return None
            if not self.es_color_hex(text_color):
                print(f"Tema invalido: {ruta_tema} tiene color de texto invalido en '{texto}'")
                return None

            colores_normalizados[texto] = {
                "color": color.upper(),
                "hover": hover.upper(),
                "text_color": text_color.upper()
            }

        return {
            "nombre": nombre.strip(),
            "colores": colores_normalizados
        }

    def es_color_hex(self, valor):
        return isinstance(valor, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", valor) is not None

    def preparar_display_temas(self):
        """Prepara los textos visibles del selector evitando nombres duplicados."""
        conteo_nombres = {}
        for tema in self.temas:
            conteo_nombres[tema["nombre"]] = conteo_nombres.get(tema["nombre"], 0) + 1

        self.tema_por_display = {}
        for tema in self.temas:
            display = tema["nombre"]
            if conteo_nombres[display] > 1:
                display = f"{tema['nombre']} ({tema['tipo']})"
            tema["display"] = display
            self.tema_por_display[display] = tema

    def seleccionar_tema_configurado(self):
        """Selecciona el tema guardado o vuelve al predefinido actual si no existe."""
        tema = self.buscar_tema(self.tema_tipo, self.tema_id) or self.buscar_tema("predefinido", "darkclassic")
        self.tema_actual = tema
        self.tema_tipo = tema["tipo"]
        self.tema_id = tema["id"]
        self.tema_var.set(tema["display"])

    def buscar_tema(self, tipo, tema_id):
        for tema in self.temas:
            if tema["tipo"] == tipo and tema["id"] == tema_id:
                return tema
        return None

    def obtener_colores_boton(self, boton):
        """Devuelve colores del tema actual para un boton rapido."""
        if self.tema_actual is None:
            return boton["color"], boton.get("hover", boton["color"]), "#FFFFFF"

        colores = self.tema_actual["colores"].get(boton["texto"], {})
        return (
            colores.get("color", boton["color"]),
            colores.get("hover", boton.get("hover", boton["color"])),
            colores.get("text_color", "#FFFFFF")
        )

    def cambiar_tema(self, display):
        """Aplica y guarda el tema seleccionado desde la lista desplegable."""
        tema = self.tema_por_display.get(display)
        if tema is None:
            return

        self.tema_actual = tema
        self.tema_tipo = tema["tipo"]
        self.tema_id = tema["id"]
        self.aplicar_tema_botones_rapidos()

        if self.ruta_teams:
            self.guardar_config()

    def aplicar_tema_botones_rapidos(self):
        """Actualiza colores de los botones rapidos ya creados."""
        if self.tema_actual is None:
            return

        for boton, config_boton in self.botones_rapidos:
            color, hover, text_color = self.obtener_colores_boton(config_boton)
            boton.configure(
                fg_color=color,
                hover_color=color,
                text_color=text_color,
                border_color=self.obtener_borde_normal_boton_rapido()
            )

    def oscurecer_color(self, color, factor=0.72):
        """Devuelve una variante mas oscura de un color hexadecimal."""
        if not self.es_color_hex(color):
            return color

        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        return f"#{int(r * factor):02X}{int(g * factor):02X}{int(b * factor):02X}"

    def obtener_borde_normal_boton_rapido(self):
        """Devuelve el borde normal de botones rapidos segun el modo visual."""
        return "#777777" if self.modo_oscuro_var.get() else "#2B2B2B"

    def mostrar_principal(self):
        """Construye la pantalla principal de mensajes y destinatarios."""
        for w in self.winfo_children():
            w.destroy()

        self.botones_rapidos = []
        self.cargar_temas()

        self.grid_columnconfigure(0, weight=7)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        """Configuración del alto del banner y su crecimiento"""
        banner_base_height = 60
        banner_max_growth_ratio = 0.80
        header_p = ctk.CTkFrame(self, fg_color="transparent")
        header_p.grid(row=0, column=0, columnspan=2, sticky="ew", padx=15, pady=(10, 0))
        header_p.grid_columnconfigure(0, weight=1)

        banner_p = ctk.CTkFrame(header_p, fg_color="transparent", height=banner_base_height)
        banner_p.grid(row=0, column=0, sticky="ew")
        banner_p.grid_propagate(False)
        header_p.grid_rowconfigure(0, minsize=banner_base_height)
        self.configurar_banner_top(header_p, banner_p, banner_base_height, banner_max_growth_ratio)

        top_p = ctk.CTkFrame(header_p, fg_color="transparent")
        top_p.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        top_p.grid_columnconfigure(0, weight=1)
        top_p.grid_rowconfigure(0, weight=1)

        alias_p = ctk.CTkFrame(top_p, fg_color="transparent")
        alias_p.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(alias_p, text="Tu alias:", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 6))
        self.btn_alias = ctk.CTkButton(
            alias_p,
            text=self.alias or self.hostname,
            height=30,
            corner_radius=8,
            command=self.editar_alias
        )
        self.btn_alias.pack(side="left")

        self.chk_inicio_windows = ctk.CTkCheckBox(
            top_p,
            text="Iniciar con Windows",
            variable=self.startup_enabled_var,
            command=lambda: self.actualizar_inicio_windows(self.startup_enabled_var.get())
        )
        self.chk_inicio_windows.grid(row=0, column=1, sticky="e", padx=(0, 10))

        tema_p = ctk.CTkFrame(top_p, fg_color="transparent")
        tema_p.grid(row=0, column=2, sticky="e", padx=(0, 10))

        ctk.CTkLabel(tema_p, text="Temas:", font=("Arial", 12, "bold")).pack(side="left", padx=(0, 6))
        self.selector_tema = ctk.CTkOptionMenu(
            tema_p,
            values=list(self.tema_por_display.keys()),
            variable=self.tema_var,
            width=150,
            command=self.cambiar_tema
        )
        self.selector_tema.pack(side="left")

        modo_p = ctk.CTkFrame(top_p, fg_color="transparent")
        modo_p.grid(row=0, column=3, sticky="e", padx=(0, 10))

        ctk.CTkLabel(modo_p, text="☀", font=("Arial", 16)).pack(side="left", padx=(0, 10))
        ctk.CTkSwitch(
            modo_p,
            text="",
            width=0,
            variable=self.modo_oscuro_var,
            command=self.alternar_modo
        ).pack(side="left")
        ctk.CTkLabel(modo_p, text="☾  | ", font=("Arial", 16)).pack(side="left", padx=(0, 0))

        self.btn_reiniciar = ctk.CTkButton(
            top_p,
            text="Volver a registrar ⚙",
            width=34,
            height=30,
            corner_radius=8,
            command=self.reiniciar_registro
        )
        self.btn_reiniciar.grid(row=0, column=4, sticky="e")

        # PANEL IZQUIERDO: MENSAJES
        left_p = ctk.CTkFrame(self)
        left_p.grid(row=1, column=0, sticky="nsew", padx=15, pady=(8, 15))
        left_p.grid_columnconfigure(0, weight=1)
        left_p.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(left_p, text="Mensajes Rápidos", font=("Arial", 18, "bold")).pack(pady=10)

        quick_p = ctk.CTkScrollableFrame(left_p, fg_color="transparent")
        quick_p.pack(expand=True, fill="both", padx=4, pady=0)

        for b in BOTONES_PRESET:
            try:
                img_path = resource_path(os.path.join("res", b["img"]))
                img = ctk.CTkImage(
                    light_image=Image.open(img_path),
                    dark_image=Image.open(img_path),
                    size=(78, 78)
                )
            except:
                img = None

            color, hover, text_color = self.obtener_colores_boton(b)
            btn = ctk.CTkButton(
                quick_p,
                text=b["texto"],
                image=img,
                fg_color=color,
                hover=False,
                hover_color=color,
                text_color=text_color,
                border_width=2,
                border_color=self.obtener_borde_normal_boton_rapido(),
                height=82,
                corner_radius=18,
                anchor="w",
                font=("Arial", 20, "bold"),
                compound="left"
            )
            btn.pack(pady=5, fill="x", padx=6)
            self.botones_rapidos.append((btn, b))
            btn.bind("<Enter>", lambda event, boton=btn, config=b: self.activar_hover_boton(boton, config))
            btn.bind("<Leave>", lambda event, boton=btn, config=b: self.desactivar_hover_boton(boton, config))
            btn.bind("<ButtonPress-1>", lambda event, boton=btn, config=b: self.iniciar_click_rapido(boton, config))
            btn.bind("<ButtonRelease-1>", lambda event, boton=btn, config=b: self.finalizar_click_rapido(event, boton, config))

        custom_p = ctk.CTkFrame(left_p, fg_color="transparent")
        custom_p.pack(fill="x", padx=24, pady=(8, 12))

        self.txt_libre = ctk.CTkEntry(custom_p, placeholder_text="Escribir mensaje personalizado...", height=40)
        self.txt_libre.pack(fill="x", pady=(0, 6))
        self.txt_libre.bind("<Return>", self.enviar_libre_con_enter)
        self.btn_enviar_personalizado = ctk.CTkButton(custom_p, text="Enviar Personalizado", command=self.enviar_libre)
        self.btn_enviar_personalizado.pack()
        self.aplicar_colores_botones_generales()

        # PANEL DERECHO: DESTINATARIOS
        right_p = ctk.CTkScrollableFrame(self, label_text="Destinatarios")
        right_p.grid(row=1, column=1, sticky="nsew", padx=15, pady=(8, 15))

        self.var_todos = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(right_p, text="ENVIAR A TODOS", font=("Arial", 12, "bold"), variable=self.var_todos, command=self.on_enviar_todos_changed).pack(anchor="w", pady=10, padx=10)

        # Escaneo de carpetas/equipos
        for equipo in os.listdir(self.ruta_teams):
            if es_destino_valido(self.ruta_teams, self.hostname, equipo):
                alias = self.obtener_alias_equipo(equipo)
                var = ctk.BooleanVar(value=False)
                self.check_vars[equipo] = var
                ctk.CTkCheckBox(right_p, text=f"{alias} ({equipo})", variable=var, command=self.on_contacto_changed).pack(anchor="w", padx=20, pady=2)

        self.confirmacion_envio = ctk.CTkFrame(
            self,
            fg_color="#DFF6E4",
            border_width=1,
            border_color="#238B45",
            corner_radius=6,
            width=400,
            height=30
        )
        self.confirmacion_envio_label = ctk.CTkLabel(
            self.confirmacion_envio,
            text="",
            text_color="#008A4A",
            font=("Arial", 12, "bold"),
            anchor="w"
        )
        self.confirmacion_envio_label.pack(fill="both", expand=True, padx=12, pady=5)
        self.confirmacion_envio.place_forget()
        self.sincronizar_inicio_windows()

    def on_contacto_changed(self):
        """Desactiva ENVIAR A TODOS cuando se activa un checkbox de contacto."""
        if any(var.get() for var in self.check_vars.values()):
            self.var_todos.set(False)

    def on_enviar_todos_changed(self):
        """Desactiva todos los checkboxes de contactos cuando se activa ENVIAR A TODOS."""
        if self.var_todos.get():
            for var in self.check_vars.values():
                var.set(False)

    def activar_hover_boton(self, boton, config_boton):
        """Aplica color hover y borde destacado para botones rapidos."""
        click = self.boton_rapido_presionado
        estado = "pressed" if click is not None and click["boton"] is boton else "hover"
        self.aplicar_estado_boton_rapido(boton, config_boton, estado)

    def desactivar_hover_boton(self, boton, config_boton):
        """Restaura el color normal y el borde al salir del hover."""
        self.aplicar_estado_boton_rapido(boton, config_boton, "normal")

    def iniciar_click_rapido(self, boton, config_boton):
        """Registra el boton rapido donde empezo el click."""
        self.boton_rapido_presionado = {
            "boton": boton,
            "texto": config_boton["texto"]
        }
        self.aplicar_estado_boton_rapido(boton, config_boton, "pressed")

    def finalizar_click_rapido(self, event, boton, config_boton):
        """Envia el mensaje rapido solo si el mouse se suelta dentro del boton."""
        click = self.boton_rapido_presionado
        self.boton_rapido_presionado = None

        if click is None or click["boton"] is not boton:
            return

        dentro = 0 <= event.x < boton.winfo_width() and 0 <= event.y < boton.winfo_height()
        if dentro:
            self.aplicar_estado_boton_rapido(boton, config_boton, "hover")
            self.enviar_rapido(click["texto"])
        else:
            self.aplicar_estado_boton_rapido(boton, config_boton, "normal")

    def aplicar_estado_boton_rapido(self, boton, config_boton, estado):
        """Aplica manualmente los colores visuales de un boton rapido."""
        color, hover, text_color = self.obtener_colores_boton(config_boton)

        if estado == "pressed":
            fg_color = self.oscurecer_color(hover)
            border_color = "#FFFFFF"
        elif estado == "hover":
            fg_color = hover
            border_color = "#FFFFFF"
        else:
            fg_color = color
            border_color = self.obtener_borde_normal_boton_rapido()

        boton.configure(
            fg_color=fg_color,
            hover_color=fg_color,
            text_color=text_color,
            border_color=border_color
        )

    def enviar(self, texto):
        """Envia un mensaje rapido o personalizado a los destinatarios elegidos."""
        if not self.ruta_teams:
            return False

        destinos = obtener_destinos(self.ruta_teams, self.hostname, self.var_todos.get(), self.check_vars)

        if not destinos:
            messagebox.showinfo("Info", "Seleccioná al menos un destinatario.")
            return False

        enviar_mensaje(self.ruta_teams, self.hostname, self.alias, destinos, texto)
        return True

    def enviar_rapido(self, texto):
        """Envia un mensaje rapido y muestra una confirmacion visual al usuario."""
        if self.enviar(texto):
            self.mostrar_confirmacion_envio(f"✅ Mensaje enviado: {texto}")

    def mostrar_confirmacion_envio(self, texto):
        """Muestra una barra flotante temporal confirmando el mensaje enviado."""
        self.confirmacion_envio_label.configure(text=texto)
        self.confirmacion_envio.place(relx=0.5, rely=1.0, y=-12, anchor="s", relwidth=0.74)
        self.confirmacion_envio.lift()

        if self.confirmacion_envio_after_id is not None:
            self.after_cancel(self.confirmacion_envio_after_id)

        self.confirmacion_envio_after_id = self.after(3000, self.ocultar_confirmacion_envio)

    def ocultar_confirmacion_envio(self):
        """Oculta la barra de confirmacion de envio."""
        self.confirmacion_envio.place_forget()
        self.confirmacion_envio_after_id = None

    def enviar_libre(self):
        """Envia el texto escrito manualmente y limpia el campo."""
        msg = self.txt_libre.get()
        if msg:
            if self.enviar(msg):
                self.mostrar_confirmacion_envio("✅ Se ha enviado el mensaje personalizado")
                self.txt_libre.delete(0, "end")

    def enviar_libre_con_enter(self, event=None):
        self.enviar_libre()
        return "break"

    def alternar_modo(self):
        """Alterna entre light y dark segun el estado del switch."""
        self.aplicar_modo_apariencia()
        self.aplicar_colores_botones_generales()
        self.aplicar_tema_botones_rapidos()

        if self.ruta_teams:
            self.guardar_config()

    def aplicar_colores_botones_generales(self):
        """Actualiza colores de botones secundarios para que contrasten en cada modo."""
        botones = [
            getattr(self, "btn_alias", None),
            getattr(self, "btn_reiniciar", None),
            getattr(self, "btn_enviar_personalizado", None)
        ]

        if self.modo_oscuro_var.get():
            colores = {
                "fg_color": "#2B2B2B",
                "hover_color": "#3A3A3A",
                "text_color": "#FFFFFF",
                "border_color": "#454545"
            }
        else:
            colores = {
                "fg_color": "#E9EEF5",
                "hover_color": "#D4DEE9",
                "text_color": "#1F2933",
                "border_color": "#9AA7B5"
            }

        for boton in botones:
            if boton is not None:
                boton.configure(
                    fg_color=colores["fg_color"],
                    hover_color=colores["hover_color"],
                    text_color=colores["text_color"],
                    border_width=1,
                    border_color=colores["border_color"]
                )

    def aplicar_modo_apariencia(self):
        """Aplica el modo visual actual sin modificar otros datos de configuracion."""
        if self.modo_oscuro_var.get():
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

    def revisar_mensajes_pendientes(self):
        revisar_mensajes_pendientes(self.ruta_teams, self.hostname, self.on_msg_received)

    def iniciar_escucha(self):
        """Activa el observer de watchdog si todavia no esta activo."""
        self.observer = iniciar_observer(
            self.ruta_teams,
            self.hostname,
            self.on_msg_received,
            self.observer
        )

    def on_msg_received(self, remitente, contenido):
        self.after(0, lambda: ToastPopup(self, remitente, contenido, on_reply=self.enviar_respuesta))

    def enviar_respuesta(self, mensaje_original, texto):
        """Envia una respuesta directa al equipo que genero el mensaje original."""
        destino = mensaje_original.get("from_hostname") if isinstance(mensaje_original, dict) else None
        if not destino:
            return

        enviar_mensaje(
            self.ruta_teams,
            self.hostname,
            self.alias,
            [destino],
            texto,
            respuesta_a=mensaje_original
        )
        self.mostrar_confirmacion_envio("Respuesta enviada")

    def detener_observer(self):
        self.observer = detener_observer(self.observer)

    def reiniciar_registro(self):
        """Borra la configuración local y reinicia la aplicación."""
        confirmar = messagebox.askyesno(
            "Volver a registrar",
            "Se borrará la configuración local y la aplicación se reiniciará para registrarla nuevamente. ¿Continuar?"
        )

        if not confirmar:
            return

        self.registrar_log_reinicio("[reinicio] Boton Volver a registrar presionado")
        executable_path = self.obtener_ruta_ejecucion_guardada()
        self.registrar_log_reinicio(f"[reinicio] Ruta de ejecucion guardada: {executable_path}")
        if not executable_path:
            self.registrar_log_reinicio("[reinicio] No se encontro ruta de ejecucion guardada")
            messagebox.showerror(
                "Error",
                "No se pudo encontrar la ruta original de BBL_Chat.exe para reiniciar la aplicación."
            )
            return

        self.mostrar_modal_reinicio()
        self.registrar_log_reinicio(f"[reinicio] Programando reinicio en {self.reinicio_delay_ms}ms")
        self._programar_reinicio(executable_path)

    def _programar_reinicio(self, executable_path):
        """Agenda el reinicio real despues de dejar visible el modal."""
        self.after(
            self.reinicio_delay_ms,
            lambda: self.ejecutar_reinicio_limpio(executable_path)
        )

    def mostrar_modal_reinicio(self):
        """Muestra una ventana modal de reinicio con imagen de fondo y barra indeterminada."""
        self.registrar_log_reinicio("[reinicio] mostrar_modal_reinicio iniciado")

        if self.reinicio_modal is not None:
            try:
                self.reinicio_modal.destroy()
            except Exception:
                pass

        self.reinicio_modal = ctk.CTkToplevel(self)
        self.reinicio_modal.title("Reiniciando...")
        self.reinicio_modal.resizable(False, False)
        self.reinicio_modal.transient(self)

        ancho = 580
        alto = 280
        self.reinicio_modal.geometry(f"{ancho}x{alto}")
        self.centrar_ventana(self.reinicio_modal, ancho, alto)

        try:
            # Imagen de fondo
            imagen_path = resource_path(os.path.join("res", "restart.png"))
            self.reinicio_bg_pil_image = Image.open(imagen_path)

            self.reinicio_bg_image = ctk.CTkImage(
                light_image=self.reinicio_bg_pil_image,
                dark_image=self.reinicio_bg_pil_image,
                size=(ancho, alto)
            )

            # Ícono de la ventana
            def aplicar_icono_reinicio():
                try:
                    if self.reinicio_modal and self.reinicio_modal.winfo_exists():
                        ico_path = resource_path(os.path.join("res", "restart_icon.ico"))
                        self.reinicio_modal.iconbitmap(ico_path)
                except Exception as e:
                    self.registrar_log_reinicio(f"[reinicio] No se pudo aplicar icono modal: {e}")

            self.reinicio_modal.after(200, aplicar_icono_reinicio)

        except Exception as e:
            self.reinicio_bg_image = None
            print(f"No se pudo cargar restart.png: {e}")

        fondo = ctk.CTkLabel(
            self.reinicio_modal,
            image=self.reinicio_bg_image,
            text=""
        )
        fondo.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            relwidth=1,
            relheight=1
        )

        barra = ctk.CTkProgressBar(
            self.reinicio_modal,
            mode="indeterminate",
            height=18,
            indeterminate_speed=1.5
        )
        barra.place(relx=0.5, rely=0.95, anchor="center", relwidth=0.85)
        barra.start()

        self.reinicio_modal.lift()
        self.reinicio_modal.focus_force()

        self.registrar_log_reinicio("[reinicio] Modal de reinicio mostrado")

    def centrar_ventana(self, ventana, ancho, alto):
        ventana.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - ancho) // 2
        y = self.winfo_y() + (self.winfo_height() - alto) // 2
        ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

    def registrar_log_reinicio(self, mensaje):
        """Escribe un log de depuracion al lado del archivo de configuración local."""
        try:
            with open(self.ruta_log_reinicio, "a", encoding="utf-8") as log_file:
                log_file.write(f"{mensaje}\n")
        except Exception:
            pass

    def ejecutar_reinicio_limpio(self, executable_path):
        """Detiene observer, borra config local y relanza la aplicación de forma limpia."""
        self.registrar_log_reinicio("[reinicio] Iniciando reinicio limpio")
        self.detener_observer()
        self.registrar_log_reinicio("[reinicio] Observer detenido")

        try:
            if os.path.exists(self.ruta_config):
                self.registrar_log_reinicio(f"[reinicio] Se encontro config: {self.ruta_config}")
                os.remove(self.ruta_config)
                self.registrar_log_reinicio("[reinicio] Configuracion eliminada correctamente")
            else:
                self.registrar_log_reinicio("[reinicio] No se encontro el archivo de configuracion para borrar")
        except Exception as e:
            self.registrar_log_reinicio(f"[reinicio] Error al borrar configuracion: {type(e).__name__}: {e}")

        try:
            if getattr(sys, "frozen", False):
                comando = [executable_path]
                cwd = os.path.dirname(executable_path)
            else:
                comando = [sys.executable, executable_path]
                cwd = os.path.dirname(executable_path)

            # ✅ Forzar instancia nueva con su propio _MEIxxxxx
            env = os.environ.copy()
            env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"

            self.registrar_log_reinicio(f"[reinicio] Ejecutando comando: {comando} en cwd={cwd}")
            subprocess.Popen(comando, cwd=cwd, env=env)
            self.registrar_log_reinicio("[reinicio] Nueva instancia lanzada correctamente")
        except Exception as e:
            self.registrar_log_reinicio(f"[reinicio] Error al lanzar nueva instancia: {type(e).__name__}: {e}")
            messagebox.showerror(
                "Error",
                f"No se pudo reiniciar la aplicación:\n{e}"
            )
            if self.reinicio_modal is not None:
                try:
                    self.reinicio_modal.destroy()
                except Exception:
                    pass
            return

        if self.reinicio_modal is not None:
            try:
                self.reinicio_modal.destroy()
            except Exception:
                pass
            self.reinicio_modal = None

        self.registrar_log_reinicio("[reinicio] Programa actual se cerrara despues del delay")
        self.after(self.cierre_reinicio_delay_ms, self.destroy)

    def on_closing(self):
        self.guardar_config()
        self.detener_observer()
        self.destroy()
