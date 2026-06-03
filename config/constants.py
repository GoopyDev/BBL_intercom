import os

# Identidad e icono de la aplicacion usados por Windows y por la ventana principal.
APP_ID = "BBL.GoopyBlack.messenger.v1"
APP_ICON = os.path.join("res", "BBL_Chat.ico")

# Configuracion visual y funcional de los botones rapidos.
# Asegurate de tener estas imagenes en tu carpeta /res.
BOTONES_PRESET = [
    {"texto": "Ayuda en Barra",   "color": "#E74C3C", "hover": "#6F251D", "img": "ayuda_btn.png"   },
    {"texto": "Snacks!",          "color": "#F1C40F", "hover": "#8A700A", "img": "snacks_btn.png"  },
    {"texto": "Hora del café",    "color": "#3498DB", "hover": "#1C5377", "img": "cafe_btn.png"    },
    {"texto": "Consulta urgente", "color": "#8E44AD", "hover": "#522764", "img": "urgente_btn.png" },
    {"texto": "A comer...!",      "color": "#D35400", "hover": "#7B3100", "img": "comida_btn.png"  },
    {"texto": "Hay facturas!",    "color": "#2ECC71", "hover": "#1B7641", "img": "facturas_btn.png"}
]

# TEMAS_PREDEFINIDOS = [
#     {
#         "id": "actual",
#         "nombre": "Actual",
#         "colores": {
#             "Ayuda en Barra":   {"color": "#E74C3C", "hover": "#6F251D"},
#             "Snacks!":          {"color": "#F1C40F", "hover": "#8A700A"},
#             "Hora del cafÃ©":   {"color": "#3498DB", "hover": "#1C5377"},
#             "Consulta urgente": {"color": "#8E44AD", "hover": "#522764"},
#             "A comer...!":      {"color": "#D35400", "hover": "#7B3100"},
#             "Hay facturas!":    {"color": "#2ECC71", "hover": "#1B7641"}
#         }
#     },
#     {
#         "id": "oficina",
#         "nombre": "Oficina",
#         "colores": {
#             "Ayuda en Barra":   {"color": "#2563EB", "hover": "#1E40AF"},
#             "Snacks!":          {"color": "#0EA5E9", "hover": "#0369A1"},
#             "Hora del cafÃ©":   {"color": "#14B8A6", "hover": "#0F766E"},
#             "Consulta urgente": {"color": "#19C175", "hover": "#0B8051"},
#             "A comer...!":      {"color": "#0BE159", "hover": "#15803D"},
#             "Hay facturas!":    {"color": "#84CC16", "hover": "#4D7C0F"}
#         }
#     },
#     {
#         "id": "vivo",
#         "nombre": "Vivo",
#         "colores": {
#             "Ayuda en Barra":   {"color": "#EF4444", "hover": "#991B1B"},
#             "Snacks!":          {"color": "#F97316", "hover": "#9A3412"},
#             "Hora del cafÃ©":   {"color": "#EAB308", "hover": "#854D0E"},
#             "Consulta urgente": {"color": "#A855F7", "hover": "#6B21A8"},
#             "A comer...!":      {"color": "#EC4899", "hover": "#9D174D"},
#             "Hay facturas!":    {"color": "#10B981", "hover": "#047857"}
#         }
#     },
#     {
#         "id": "profundo",
#         "nombre": "Profundo",
#         "colores": {
#             "Ayuda en Barra":   {"color": "#7F1D1D", "hover": "#450A0A"},
#             "Snacks!":          {"color": "#92400E", "hover": "#451A03"},
#             "Hora del cafÃ©":   {"color": "#1E3A8A", "hover": "#172554"},
#             "Consulta urgente": {"color": "#581C87", "hover": "#3B0764"},
#             "A comer...!":      {"color": "#064E3B", "hover": "#022C22"},
#             "Hay facturas!":    {"color": "#365314", "hover": "#1A2E05"}
#         }
#     }
# ]

def _tema_colores(pares):
    colores = {}
    for boton, par in zip(BOTONES_PRESET, pares):
        color, hover = par[:2]
        text_color = par[2] if len(par) > 2 else "#FFFFFF"
        colores[boton["texto"]] = {
            "color": color,
            "hover": hover,
            "text_color": text_color
        }
    return colores


TEMAS_PREDEFINIDOS = [
    {
        "id": "darkclassic",
        "nombre": "Dark Classic",
        "colores": _tema_colores([
            ("#E74C3C", "#6F251D", "#FFFFFF"),
            ("#F1C40F", "#8A700A", "#FFFFFF"),
            ("#3498DB", "#1C5377", "#FFFFFF"),
            ("#8E44AD", "#522764", "#FFFFFF"),
            ("#D35400", "#7B3100", "#FFFFFF"),
            ("#2ECC71", "#1B7641", "#FFFFFF")
        ])
    },
    {
        "id": "oficina",
        "nombre": "Oficina",
        "colores": _tema_colores([
            ("#2563EB", "#1E40AF", "#FFFFFF"),
            ("#0EA5E9", "#0369A1", "#FFFFFF"),
            ("#14B8A6", "#0F766E", "#FFFFFF"),
            ("#19C175", "#0B8051", "#FFFFFF"),
            ("#22C55E", "#15803D", "#FFFFFF"),
            ("#84CC16", "#4D7C0F", "#1F2933")
        ])
    },
    {
        "id": "vivo",
        "nombre": "Vivo",
        "colores": _tema_colores([
            ("#EF4444", "#991B1B", "#FFFFFF"),
            ("#F97316", "#9A3412", "#FFFFFF"),
            ("#EAB308", "#854D0E", "#1F2933"),
            ("#A855F7", "#6B21A8", "#FFFFFF"),
            ("#EC4899", "#9D174D", "#FFFFFF"),
            ("#10B981", "#047857", "#FFFFFF")
        ])
    },
    {
        "id": "profundo",
        "nombre": "Profundo",
        "colores": _tema_colores([
            ("#7F1D1D", "#450A0A", "#FFFFFF"),
            ("#92400E", "#451A03", "#FFFFFF"),
            ("#1E3A8A", "#172554", "#FFFFFF"),
            ("#581C87", "#3B0764", "#FFFFFF"),
            ("#064E3B", "#022C22", "#FFFFFF"),
            ("#365314", "#1A2E05", "#FFFFFF")
        ])
    }
]

# Fondos disponibles para cada mensaje. Las claves se mantienen tal como estaban
# para no modificar el comportamiento actual de seleccion de imagenes.
FONDOS_POPUP = {
    "Ayuda en Barra": [
        "ayuda1.png",
        "ayuda2.png",
        "ayuda3.png"
    ],

    "Snacks!": [
        "snacks.png",
    ],

    "Hora del café": [
        "cafe.png",
    ],

    "Consulta urgente": [
        "urgente.png"
    ],

    "A comer...!": [
        "comida.png"
    ],

    "Hay facturas!": [
        "facturas.png",
    ]
}
