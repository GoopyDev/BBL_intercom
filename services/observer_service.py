import os
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from services.message_service import parsear_mensaje, revisar_mensajes_pendientes


class ManejadorMensajes(FileSystemEventHandler):
    """Handler de watchdog para archivos .txt creados en la carpeta del equipo."""
    def __init__(self, callback):
        self.callback = callback

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".txt"):
            try:
                # Pequeña pausa para asegurar que el archivo termino de escribirse/sincronizarse.
                time.sleep(0.5)
                with open(event.src_path, "r", encoding="utf-8") as f:
                    contenido = f.read()
                remitente = os.path.basename(event.src_path).split("_")[0]
                self.callback(remitente, parsear_mensaje(remitente, contenido))
                os.remove(event.src_path)
            except Exception as e:
                print(f"Error al leer mensaje: {e}")


def iniciar_observer(ruta_teams, hostname, callback, observer_actual=None):
    """Inicia watchdog y procesa mensajes que hayan quedado pendientes."""
    if observer_actual:
        return observer_actual

    path = os.path.join(ruta_teams, hostname)

    revisar_mensajes_pendientes(ruta_teams, hostname, callback)

    handler = ManejadorMensajes(callback)

    observer = Observer()
    observer.schedule(handler, path, recursive=False)
    observer.start()
    return observer


def detener_observer(observer):
    """Detiene watchdog de forma ordenada si esta activo."""
    if observer:
        observer.stop()
        observer.join()
    return None
