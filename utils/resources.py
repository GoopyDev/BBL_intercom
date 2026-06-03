import os
import sys


def resource_path(relative_path):
    """Devuelve la ruta correcta para desarrollo y para ejecutables PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
