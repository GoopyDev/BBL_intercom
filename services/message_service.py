import datetime
import json
import os
import uuid


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


def crear_payload_mensaje(hostname, alias, texto, respuesta_a=None):
    """Crea el formato enriquecido de mensaje manteniendo el texto como dato principal."""
    payload = {
        "version": 1,
        "id": uuid.uuid4().hex,
        "from_hostname": hostname,
        "from_alias": alias,
        "text": texto,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds")
    }

    if respuesta_a:
        payload["reply_to"] = {
            "id": respuesta_a.get("id"),
            "from_hostname": respuesta_a.get("from_hostname"),
            "from_alias": respuesta_a.get("from_alias") or respuesta_a.get("sender") or "",
            "text": respuesta_a.get("text") or ""
        }

    return payload


def parsear_mensaje(remitente_archivo, contenido):
    """Normaliza mensajes nuevos en JSON y mensajes viejos en texto plano."""
    try:
        data = json.loads(contenido)
    except json.JSONDecodeError:
        data = None

    if not isinstance(data, dict) or "text" not in data:
        return {
            "version": 0,
            "id": None,
            "from_hostname": None,
            "from_alias": remitente_archivo,
            "text": contenido,
            "created_at": None,
            "reply_to": None
        }

    texto = data.get("text")
    if not isinstance(texto, str):
        texto = str(texto)

    return {
        "version": data.get("version", 1),
        "id": data.get("id"),
        "from_hostname": data.get("from_hostname"),
        "from_alias": data.get("from_alias") or remitente_archivo,
        "text": texto,
        "created_at": data.get("created_at"),
        "reply_to": data.get("reply_to") if isinstance(data.get("reply_to"), dict) else None
    }


def enviar_mensaje(ruta_teams, hostname, alias, destinos, texto, respuesta_a=None):
    """Escribe un archivo .txt por destinatario en la carpeta compartida."""
    if not ruta_teams:
        return

    payload = crear_payload_mensaje(hostname, alias, texto, respuesta_a)
    contenido = json.dumps(payload, ensure_ascii=False)

    for d in destinos:
        if not es_destino_valido(ruta_teams, hostname, d):
            continue

        f_path = os.path.join(ruta_teams, d)
        f_name = f"{alias}_{datetime.datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:6]}.txt"
        try:
            with open(os.path.join(f_path, f_name), "w", encoding="utf-8") as f:
                f.write(contenido)
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

            callback(remitente, parsear_mensaje(remitente, contenido))

            os.remove(full_path)

        except Exception as e:
            print(f"Error leyendo mensaje pendiente: {e}")
