import json
import os
import sys

import customtkinter as ctk

RUTA_ICONO = os.path.abspath(os.path.join(os.path.dirname(__file__), "res", "BBL_Chat.ico"))

# Todas las ventanas secundarias CTk reciben el icono desde este punto de entrada.
_original_toplevel_init = ctk.CTkToplevel.__init__


def _patched_toplevel_init(self, *args, **kwargs):
    _original_toplevel_init(self, *args, **kwargs)
    if os.path.exists(RUTA_ICONO):
        def aplicar_icono_personalizado():
            if self.winfo_exists():
                self.iconbitmap(RUTA_ICONO)

        # CustomTkinter reaplica su icono por defecto a los 200 ms.
        self.after(10, aplicar_icono_personalizado)
        self.after(202, aplicar_icono_personalizado)
        self.after(250, aplicar_icono_personalizado)


ctk.CTkToplevel.__init__ = _patched_toplevel_init

from ui.already_running_dialog import AlreadyRunningDialog
from ui.main_window import ITMessenger
from ui.splash_screen import SplashScreen
from utils.single_instance import SingleInstanceController


def cargar_ventana_guardada():
    ruta_config = os.path.join(os.environ.get("APPDATA", ""), "IT_Messenger_Config.json")
    if not ruta_config or not os.path.exists(ruta_config):
        return None

    try:
        with open(ruta_config, "r", encoding="utf-8") as f:
            data = json.load(f)
        ventana = data.get("ventana")
        if isinstance(ventana, dict):
            if all(isinstance(ventana.get(key), int) for key in ("x", "y", "width", "height")):
                return ventana
    except Exception:
        pass

    return None


SPLASH_GIF_PATH = os.path.join("res", "TechDance.gif")
SPLASH_PLAYBACK_SPEED = 4 #2.3  # 1.0 = velocidad normal, 2.0 = 2x rápido, 0.5 = mitad de velocidad
SPLASH_TARGET_SIZE = (333, 400)  # Ej: (640, 360) para forzar un tamaño fijo; None usa el tamaño original del GIF


if __name__ == "__main__":
    ventana_guardada = cargar_ventana_guardada()
    controller = SingleInstanceController()
    if not controller.acquire():
        hwnd = controller.activate_existing_window()

        root = ctk.CTk()
        root.withdraw()
        dialog = AlreadyRunningDialog(parent=root, anchor_hwnd=hwnd, anchor_geometry=ventana_guardada)
        dialog.show_over_parent()
        root.mainloop()
        root.destroy()
        sys.exit(0)

    splash = SplashScreen(
        SPLASH_GIF_PATH,
        last_geometry=ventana_guardada,
        playback_speed=SPLASH_PLAYBACK_SPEED,
        target_size=SPLASH_TARGET_SIZE,
    )
    if splash.loaded:
        splash.show()

    app = ITMessenger(single_instance_controller=controller)
    app.mainloop()
    controller.release()

# Para compilar:
# pyinstaller --onefile --windowed --name BBL_Chat --icon=res/BBL_Chat.ico --add-data "res;res" --hidden-import=PIL --hidden-import=customtkinter --hidden-import=watchdog.events --hidden-import=watchdog.observers --hidden-import=watchdog.observers.api --hidden-import=watchdog.observers.read_directory_changes --hidden-import=watchdog.observers.winapi --hidden-import=winshell --hidden-import=win32com --hidden-import=win32com.client main.py
