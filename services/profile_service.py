import json
import os


def actualizar_profile_equipo(ruta_teams, hostname, alias):
    """Crea o actualiza el profile.json del equipo actual."""
    if not ruta_teams:
        return

    try:
        equipo_path = os.path.join(ruta_teams, hostname)
        os.makedirs(equipo_path, exist_ok=True)

        profile_path = os.path.join(equipo_path, "profile.json")
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump({
                "hostname": hostname,
                "alias": alias or hostname
            }, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error actualizando profile.json: {e}")


def obtener_alias_equipo(ruta_teams, hostname):
    """Lee el alias del profile.json de un equipo remoto."""
    try:
        profile_path = os.path.join(ruta_teams, hostname, "profile.json")
        with open(profile_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data.get("alias") or hostname
    except Exception:
        return hostname
