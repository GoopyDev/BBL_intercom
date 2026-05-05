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
from plyer import notification

# --- FUNCIÓN PARA RUTAS DE RECURSOS (VITAL PARA EL EXE) ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- CONFIGURACIÓN DE BOTONES ---
# Asegurate de tener estas imágenes en tu carpeta /resources
BOTONES_PRESET = [
    {"texto": "Ayuda en Barra", "color": "#E74C3C", "img": "ayuda.png"},
    {"texto": "¡Snacks!", "color": "#F1C40F", "img": "snacks.png"},
    {"texto": "Hora del café", "color": "#3498DB", "img": "cafe.png"},
    {"texto": "Consulta urgente", "color": "#8E44AD", "img": "urgente.png"},
    {"texto": "¡Hay facturas!", "color": "#2ECC71", "img": "comida.png"}
]

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

class ITMessenger(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.hostname = socket.gethostname().upper()
        self.ruta_config = os.path.join(os.environ['APPDATA'], "IT_Messenger_Config.json")
        self.ruta_teams = ""
        self.alias = ""
        self.check_vars = {}

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
                img_path = resource_path(os.path.join("resources", b["img"]))
                img = ctk.CTkImage(light_image=Image.open(img_path), size=(25, 25))
            except:
                img = None

            btn = ctk.CTkButton(left_p, text=b["texto"], image=img, fg_color=b["color"], 
                                height=55, font=("Arial", 14, "bold"), compound="left",
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

    def iniciar_escucha(self):
        path = os.path.join(self.ruta_teams, self.hostname)
        handler = ManejadorMensajes(self.on_msg_received)
        self.observer = Observer()
        self.observer.schedule(handler, path, recursive=False)
        self.observer.start()

    def on_msg_received(self, remitente, contenido):
        # Ejecutar en el hilo de la UI
        self.after(0, lambda: notification.notify(
            title=f"Mensaje de {remitente}",
            message=contenido,
            app_name="IT Messenger",
            timeout=10 # Duración en segundos
        ))

if __name__ == "__main__":
    app = ITMessenger()
    app.mainloop()