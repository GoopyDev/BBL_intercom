import os


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def formatear_nombre_categoria(nombre, es_archivo=False):
    """Convierte nombres de archivos y carpetas en etiquetas legibles."""
    if es_archivo:
        nombre = os.path.splitext(nombre)[0]
    return nombre.replace("_", " ").strip()


def _primer_archivo_imagen(items):
    for item in items:
        image = item.get("image")
        if image:
            return image
        children = item.get("items") or []
        image = _primer_archivo_imagen(children)
        if image:
            return image
    return None


def _cargar_items(ruta):
    items = []
    try:
        entradas = sorted(os.scandir(ruta), key=lambda entry: entry.name.casefold())
    except OSError:
        return items

    for entrada in entradas:
        if entrada.is_file() and os.path.splitext(entrada.name)[1].lower() in IMAGE_EXTENSIONS:
            items.append({
                "label": formatear_nombre_categoria(entrada.name, es_archivo=True),
                "image": os.path.abspath(entrada.path),
                "category_image": os.path.abspath(entrada.path),
                "items": []
            })
        elif entrada.is_dir():
            children = _cargar_items(entrada.path)
            if children:
                items.append({
                    "label": formatear_nombre_categoria(entrada.name),
                    "items": children,
                    "category_image": _primer_archivo_imagen(children)
                })

    return items


def cargar_categorias(ruta_mensajes):
    """Carga las categorias de respuestas rapidas desde Categories."""
    if not ruta_mensajes:
        return {}

    ruta_categories = os.path.join(ruta_mensajes, "Categories")
    if not os.path.isdir(ruta_categories):
        return {}

    categorias = {}
    try:
        entradas = sorted(os.scandir(ruta_categories), key=lambda entry: entry.name.casefold())
    except OSError:
        return categorias

    for entrada in entradas:
        if not entrada.is_dir():
            continue
        items = _cargar_items(entrada.path)
        if items:
            categorias[entrada.name.casefold()] = {
                "items": items,
                "default_image": _primer_archivo_imagen(items),
                "source_path": os.path.abspath(entrada.path)
            }

    return categorias
