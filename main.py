import os
import sys
import socket
import json
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import ctypes
# Esto le dice a Windows que trate a este proceso como una aplicación con identidad propia
myappid = 'BBL.GoopyBlack.messenger.v1' # Puedes inventar cualquier nombre con este formato
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

# --- FUNCIÓN PARA RUTAS DE RECURSOS (VITAL PARA EL EXE) ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- CONFIGURACIÓN DE BOTONES ---
# Asegurate de tener estas imágenes en tu carpeta /res
BOTONES_PRESET = [
    {"texto": "Ayuda en Barra",  "color": "#E74C3C", "img": "ayuda_btn.png"  },
    {"texto": "¡Snacks!",        "color": "#F1C40F", "img": "snacks_btn.png" },
    {"texto": "Hora del café",   "color": "#3498DB", "img": "cafe_btn.png"   },
    {"texto": "Consulta urgente","color": "#8E44AD", "img": "urgente_btn.png"},
    {"texto": "¡Hay facturas!",  "color": "#2ECC71", "img": "comida_btn.png" }
]

FONDOS_POPUP = {
    "Ayuda en Barra": [
        "barra1.png",
        "barra2.png",
        "barra3.png"
    ],

    "¡Snacks!": [
        "snack1.png",
        "snack2.png"
    ],

    "Hora del café": [
        "cafe1.png",
        "cafe2.png"
    ],

    "Consulta urgente": [
        "urgente1.png"
    ],

    "¡Hay facturas!": [
        "factura1.png",
        "factura2.png"
    ]
}

ROTACION_FONDOS = {}

def obtener_fondo_popup(mensaje):
    fondos = FONDOS_POPUP.get(mensaje)

    if not fondos:
        return None

    # índice actual
    idx = ROTACION_FONDOS.get(mensaje, 0)

    fondo = fondos[idx]

    # avanzar rotación
    idx += 1

    if idx >= len(fondos):
        idx = 0

    ROTACION_FONDOS[mensaje] = idx

    return fondo

class ManejadorMensajes(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".txt"):
            try:
                # Pequeña pausa para asegurar que el archivo terminó de escribirse/sincronizarse
                import time
                time.sleep(0.5)
                with open(event.src_path, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                remitente = os.path.basename(event.src_path).split('_')[0]
                self.callback(remitente, contenido)
                os.remove(event.src_path)
            except Exception as e:
                print(f"Error al leer mensaje: {e}")

class ToastPopup(ctk.CTkToplevel):
    def __init__(self, master, remitente, mensaje):
        super().__init__(master)

        self.width = 360
        self.height = 120

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0)

        # Posición esquina inferior derecha
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        x = screen_w - self.width - 20
        y = screen_h - self.height - 60

        self.current_y = y + 20
        self.target_y = y
        self.geometry(f"{self.width}x{self.height}+{x}+{self.current_y}")

        # Frame principal
        self.main = ctk.CTkFrame(
            self,
            corner_radius=18,
            fg_color="#202123",
            border_width=1,
            border_color="#3A3B3C"
        )
        self.main.pack(fill="both", expand=True)

        # # Imagen/icono
        # img_path = resource_path(os.path.join("res", "mensaje.png"))

        # try:
        #     img = ctk.CTkImage(
        #         light_image=Image.open(img_path),
        #         dark_image=Image.open(img_path),
        #         size=(55, 55)
        #     )

        #     self.img_label = ctk.CTkLabel(
        #         self.main,
        #         image=img,
        #         text=""
        #     )
        #     self.img_label.place(x=15, y=30)

        # except:
        #     pass
        # -------------------------
        # FONDO DINÁMICO
        # -------------------------
        fondo = obtener_fondo_popup(mensaje)

        if fondo:
            try:
                fondo_path = resource_path(os.path.join("res", fondo))

                bg_img = ctk.CTkImage(
                    light_image=Image.open(fondo_path),
                    dark_image=Image.open(fondo_path),
                    size=(self.width, self.height)
                )

                self.bg_label = ctk.CTkLabel(
                    self.main,
                    image=bg_img,
                    text=""
                )

                self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

            except Exception as e:
                print(f"Error cargando fondo: {e}")
                    
            self.overlay = ctk.CTkFrame(
            self.main,
            fg_color="#000000",
            corner_radius=18
        )

        self.overlay.place(
            relwidth=1,
            relheight=1
        )

        self.overlay.configure(fg_color=("black", "black"))

        # Remitente
        self.title_label = ctk.CTkLabel(
            self.main,
            text=remitente,
            font=("Segoe UI", 15, "bold"),
            anchor="w"
        )
        self.title_label.place(x=85, y=20)

        # Mensaje
        self.msg_label = ctk.CTkLabel(
            self.main,
            text=mensaje,
            font=("Segoe UI", 13),
            justify="left",
            wraplength=240,
            anchor="w"
        )
        self.msg_label.place(x=85, y=50)

        # Botón cerrar
        self.close_btn = ctk.CTkButton(
            self.main,
            text="✕",
            width=28,
            height=28,
            corner_radius=50,
            fg_color="transparent",
            hover_color="#333",
            command=self.close_animation
        )
        self.close_btn.place(x=320, y=10)

        self.fade_in()

    def fade_in(self):
        alpha = self.attributes("-alpha")

        if alpha < 0.98:
            alpha += 0.06

            self.attributes("-alpha", alpha)

            # movimiento hacia arriba
            if self.current_y > self.target_y:
                self.current_y -= 2

            self.geometry(
                f"{self.width}x{self.height}+"
                f"{self.winfo_x()}+{int(self.current_y)}"
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
                f"{self.winfo_x()}+{int(self.current_y)}"
            )

            self.after(16, self.close_animation)

        else:
            self.destroy()

class ITMessenger(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.hostname = socket.gethostname().upper()
        self.ruta_config = os.path.join(os.environ['APPDATA'], "IT_Messenger_Config.json")
        self.ruta_teams = ""
        self.alias = ""
        self.check_vars = {}
        self.observer = None

        self.cargar_config()
        self.setup_ui()

    def cargar_config(self):
        if os.path.exists(self.ruta_config):
            with open(self.ruta_config, 'r') as f:
                data = json.load(f)
                self.ruta_teams = data.get("ruta")
                self.alias = data.get("alias")
            self.iniciar_escucha()

    def setup_ui(self):
        self.title(f"IT Messenger - {self.hostname}")
        self.geometry("750x600")
        ctk.set_appearance_mode("dark")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        if not self.ruta_teams:
            self.mostrar_registro()
        else:
            self.mostrar_principal()

    def mostrar_registro(self):
        self.reg_frame = ctk.CTkFrame(self)
        self.reg_frame.pack(expand=True, fill="both", padx=40, pady=40)
        
        ctk.CTkLabel(self.reg_frame, text="Registro de Equipo", font=("Arial", 24, "bold")).pack(pady=20)
        self.ent_alias = ctk.CTkEntry(self.reg_frame, placeholder_text="Tu Alias o Nombre...", height=40)
        self.ent_alias.pack(pady=10, fill="x", padx=60)
        
        ctk.CTkButton(self.reg_frame, text="Vincular Carpeta Compartida", command=self.vincular).pack(pady=10)
        self.lbl_info = ctk.CTkLabel(self.reg_frame, text="Ruta no seleccionada", text_color="gray")
        self.lbl_info.pack()

    def vincular(self):
        ruta = filedialog.askdirectory()
        if ruta:
            alias = self.ent_alias.get() or self.hostname
            os.makedirs(os.path.join(ruta, self.hostname), exist_ok=True)
            with open(self.ruta_config, 'w') as f:
                json.dump({"ruta": ruta, "alias": alias}, f)
            
            self.ruta_teams = ruta
            self.alias = alias
            self.iniciar_escucha()
            self.mostrar_principal()

    def mostrar_principal(self):
        for w in self.winfo_children(): w.destroy()
        
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # PANEL IZQUIERDO: MENSAJES
        left_p = ctk.CTkFrame(self)
        left_p.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        
        ctk.CTkLabel(left_p, text="Mensajes Rápidos", font=("Arial", 18, "bold")).pack(pady=10)

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

            btn = ctk.CTkButton(left_p, text=b["texto"], image=img, fg_color=b["color"], 
                                height=82, corner_radius=18, anchor="w", font=("Arial", 20, "bold"), compound="left",
                                command=lambda t=b["texto"]: self.enviar(t))
            btn.pack(pady=6, fill="x", padx=15)

        self.txt_libre = ctk.CTkEntry(left_p, placeholder_text="Escribir mensaje personalizado...", height=40)
        self.txt_libre.pack(pady=(20, 5), fill="x", padx=15)
        ctk.CTkButton(left_p, text="Enviar Personalizado", fg_color="#555", command=self.enviar_libre).pack(pady=10)

        # PANEL DERECHO: DESTINATARIOS
        right_p = ctk.CTkScrollableFrame(self, label_text="Destinatarios")
        right_p.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)

        self.var_todos = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(right_p, text="ENVIAR A TODOS", font=("Arial", 12, "bold"), variable=self.var_todos).pack(anchor="w", pady=10, padx=10)
        
        # Escaneo de carpetas/equipos
        for equipo in os.listdir(self.ruta_teams):
            if equipo != self.hostname and os.path.isdir(os.path.join(self.ruta_teams, equipo)):
                var = ctk.BooleanVar(value=False)
                self.check_vars[equipo] = var
                ctk.CTkCheckBox(right_p, text=equipo, variable=var).pack(anchor="w", padx=20, pady=2)

    def enviar(self, texto):
        if not self.ruta_teams: return
        
        destinos = []
        if self.var_todos.get():
            destinos = [d for d in os.listdir(self.ruta_teams) if d != self.hostname and os.path.isdir(os.path.join(self.ruta_teams, d))]
        else:
            destinos = [h for h, v in self.check_vars.items() if v.get()]

        if not destinos:
            messagebox.showinfo("Info", "Seleccioná al menos un destinatario.")
            return

        for d in destinos:
            f_path = os.path.join(self.ruta_teams, d)
            f_name = f"{self.alias}_{datetime.datetime.now().strftime('%H%M%S')}.txt"
            try:
                with open(os.path.join(f_path, f_name), "w", encoding='utf-8') as f:
                    f.write(texto)
            except: pass

    def enviar_libre(self):
        msg = self.txt_libre.get()
        if msg:
            self.enviar(msg)
            self.txt_libre.delete(0, 'end')

    def revisar_mensajes_pendientes(self):
        path = os.path.join(self.ruta_teams, self.hostname)

        if not os.path.exists(path):
            return

        archivos = sorted([
            f for f in os.listdir(path)
            if f.endswith(".txt")
        ])

        for archivo in archivos:
            full_path = os.path.join(path, archivo)

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    contenido = f.read()

                remitente = archivo.split('_')[0]

                self.on_msg_received(remitente, contenido)

                os.remove(full_path)

            except Exception as e:
                print(f"Error leyendo mensaje pendiente: {e}")

    def iniciar_escucha(self):
        # Chequear si ya hay observer
        if self.observer:
            return

        path = os.path.join(self.ruta_teams, self.hostname)

        self.revisar_mensajes_pendientes()

        handler = ManejadorMensajes(self.on_msg_received)

        self.observer = Observer()
        self.observer.schedule(handler, path, recursive=False)
        self.observer.start()

    def on_msg_received(self, remitente, contenido):
        self.after(0, lambda: ToastPopup(self, remitente, contenido))

    def on_closing(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()

        self.destroy()

if __name__ == "__main__":
    app = ITMessenger()
    app.mainloop()