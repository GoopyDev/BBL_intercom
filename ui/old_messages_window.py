import datetime
import os

import customtkinter as ctk
from PIL import Image

from utils.resources import resource_path


class OldMessagesWindow(ctk.CTkToplevel):
    """Ventana de consulta de mensajes recibidos con antiguedad configurada."""

    def __init__(self, master, messages, hours):
        super().__init__(master)
        self.title("Mensajes anteriores")
        self.geometry("620x800")
        self.minsize(300, 360)
        self.transient(master)
        self.update_idletasks()
        parent_x = master.winfo_rootx()
        parent_y = master.winfo_rooty()
        self.geometry(f"620x800+{parent_x}+{parent_y}")
        self.update_idletasks()
        decoration_x = self.winfo_rootx() - parent_x
        decoration_y = self.winfo_rooty() - parent_y
        self.geometry(f"620x800+{parent_x - decoration_x}+{parent_y - decoration_y}")
        self.lift()
        self.focus_force()
        self._messages = messages
        self._hours = hours
        self._border_color = "#64748B" if ctk.get_appearance_mode().lower() == "light" else "#CBD5E1"
        self._background = ("#F8FAFC", "#111827")
        self._header_image_pil = None
        self._header_image = None
        self._header_label = None
        self._header = None
        self.configure(fg_color=self._background)
        self._build()

    def _build(self):
        frame = ctk.CTkFrame(self, fg_color=self._background, border_width=3, border_color=self._border_color, corner_radius=0)
        frame.pack(fill="both", expand=True)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(frame, fg_color=self._background, height=112, corner_radius=0)
        self._header = header
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        try:
            self._header_image_pil = Image.open(resource_path(os.path.join("res", "MenasajesAnteriores.png")))
            self._header_image = ctk.CTkImage(
                light_image=self._header_image_pil,
                dark_image=self._header_image_pil,
                size=(600, 108)
            )
            self._header_label = ctk.CTkLabel(header, image=self._header_image, text="")
            self._header_label.pack(fill="both", expand=True)
            self.bind("<Configure>", self._ajustar_header)
        except Exception:
            ctk.CTkLabel(header, text="Mensajes anteriores", font=("Arial", 22, "bold")).pack(expand=True)

        ctk.CTkFrame(frame, height=3, fg_color=self._border_color, corner_radius=0).grid(row=0, column=0, sticky="sew")
        self.text = ctk.CTkTextbox(
            frame,
            wrap="word",
            font=("Consolas", 12),
            fg_color=("#FFFFFF", "#1F2937"),
            text_color=("#111827", "#F8FAFC"),
            border_width=0,
            corner_radius=0,
            activate_scrollbars=True
        )
        self.text.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
        self._populate()

    def _ajustar_header(self, event=None):
        if self._header_image_pil is None or self._header_image is None:
            return

        width = max(300, self.winfo_width() - 6)
        image_width, image_height = self._header_image_pil.size
        height = max(1, round(width * image_height / image_width))
        self._header.configure(height=height)
        self._header_image.configure(size=(width, height))

    def _populate(self):
        if not self._messages:
            self.text.insert("1.0", f"No hay mensajes con mas de {self._hours} horas.\n")
        else:
            for message in self._messages:
                created_at = message.get("created_at") or "Fecha desconocida"
                try:
                    created_at = datetime.datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
                    stamp = created_at.strftime("%d/%m/%Y %H:%M")
                except ValueError:
                    stamp = str(created_at)
                sender = message.get("from_alias") or message.get("from_hostname") or "Remitente desconocido"
                recipients = ", ".join(message.get("to") or []) or "Destinatarios no informados"
                self.text.insert("end", f"Remitente: {sender}\nHora y fecha: {stamp}\nEnviado a: {recipients}\n\n")
                self.text.insert("end", f"{message.get('text', '')}\n\n{'-' * 72}\n\n")
        self.text.configure(state="disabled")
