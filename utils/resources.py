import os
import sys
import tkinter as tk

from config.constants import APP_ICON


def resource_path(relative_path):
    """Devuelve la ruta correcta para desarrollo y para ejecutables PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    return os.path.join(base_path, relative_path)


def aplicar_icono_ventana(window):
    """Aplica el icono de la aplicacion a una ventana Tkinter real."""
    if window is None:
        return False

    icon_path = os.path.abspath(resource_path(APP_ICON))
    png_path = os.path.splitext(icon_path)[0] + ".PNG"

    try:
        if sys.platform.startswith("win"):
            if not os.path.isfile(icon_path):
                raise FileNotFoundError(icon_path)
            window.iconbitmap(icon_path)
            return True

        if not os.path.isfile(png_path):
            raise FileNotFoundError(png_path)
        icon_photo = tk.PhotoImage(file=png_path)
        window.iconphoto(False, icon_photo)
        window._app_icon_photo = icon_photo
        return True
    except Exception:
        return False
