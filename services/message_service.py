import datetime
import os


CARPETAS_RESERVADAS = {"Themes"}


def es_destino_valido(ruta_teams, hostname, nombre):
    """Indica si una carpeta representa un equipo destinatario."""
    return (
        nombre != hostname
        and nombre not in CARPETAS_RESERVADAS
        and os.path.isdir(os.path.join(ruta_teams, nombre))
    )


def obtener_destinos(ruta_teams, hostname, enviar_a_todos, check_vars):
    """Calcula destinatarios usando la misma logica de seleccion de la UI."""
    if enviar_a_todos:
        return [
            d for d in os.listdir(ruta_teams)
            if es_destino_valido(ruta_teams, hostname, d)
        ]

    return [h for h, v in check_vars.items() if v.get() and es_destino_valido(ruta_teams, hostname, h)]


def enviar_mensaje(ruta_teams, hostname, alias, destinos, texto):
    """Escribe un archivo .txt por destinatario en la carpeta compartida."""
    if not ruta_teams:
        return

    for d in destinos:
        if not es_destino_valido(ruta_teams, hostname, d):
            continue

        f_path = os.path.join(ruta_teams, d)
        f_name = f"{alias}_{datetime.datetime.now().strftime('%H%M%S')}.txt"
        try:
            with open(os.path.join(f_path, f_name), "w", encoding="utf-8") as f:
                f.write(texto)
        except:
            pass


def revisar_mensajes_pendientes(ruta_teams, hostname, callback):
    """Lee mensajes pendientes del equipo local y los elimina al procesarlos."""
    path = os.path.join(ruta_teams, hostname)

    if not os.path.exists(path):
        return

    archivos = sorted([
        f for f in os.listdir(path)
        if f.endswith(".txt")
    ])

    for archivo in archivos:
        full_path = os.path.join(path, archivo)

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                contenido = f.read()

            remitente = archivo.split("_")[0]

            callback(remitente, contenido)

            os.remove(full_path)

        except Exception as e:
            print(f"Error leyendo mensaje pendiente: {e}")
