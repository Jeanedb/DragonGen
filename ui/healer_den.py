import customtkinter as ctk
from PIL import Image, ImageTk
import tkinter as tk
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class HealerDenWindow(ctk.CTkToplevel):
    def __init__(self, parent, world):
        super().__init__(parent)

        self.parent = parent
        self.world = world

        self.title("Healer's Den")
        self.geometry("900x650")
        self.minsize(700, 500)

        self.transient(parent)
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self.lift()
        self.focus_force()

        self.create_layout()

    
    def set_background(self, image_path):
        self.bg_raw = Image.open(resource_path(image_path))

        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        def resize_bg(event):
            w = event.width
            h = event.height

            resized = self.bg_raw.resize((w, h))
            self.bg_image = ImageTk.PhotoImage(resized)

            self.canvas.delete("bg")
            self.canvas.create_image(0, 0, image=self.bg_image, anchor="nw", tags="bg")
            self.canvas.tag_lower("bg")

        self.canvas.bind("<Configure>", resize_bg)


    def create_layout(self):
        self.set_background("assets/menu/healer_bg.png")

        content = ctk.CTkFrame(self.canvas, fg_color="#111111", corner_radius=28)
        self.canvas.create_window(350, 325, anchor="center", window=content, width=700, height=560)
        title = ctk.CTkLabel(
            content,
            text="Healer's Den",
            font=("Arial", 22, "bold")
        )
        title.pack(pady=(18, 4))

        subtitle = ctk.CTkLabel(
            content,
            text="Review injured dragons and the healers available to care for them.",
            font=("Arial", 13),
            text_color="#BDBDBD"
        )
        subtitle.pack(pady=(0, 14))

        body = ctk.CTkFrame(content, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=10)

        injured_frame = ctk.CTkFrame(body, fg_color="#202020", corner_radius=14)
        injured_frame.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)

        healer_frame = ctk.CTkFrame(body, fg_color="#202020", corner_radius=14)
        healer_frame.pack(side="right", fill="both", expand=True, padx=(8, 0), pady=8)

        injured_title = ctk.CTkLabel(
            injured_frame,
            text="Injured Dragons",
            font=("Arial", 18, "bold"),
            text_color="#F2C94C"
        )
        injured_title.pack(anchor="w", padx=12, pady=(12, 6))

        injured_scroll = ctk.CTkScrollableFrame(injured_frame)
        injured_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        injured_dragons = [
            d for d in self.world.dragons
            if getattr(d, "status", "") == "Alive"
            and getattr(d, "health", "Healthy") != "Healthy"
        ]

        if injured_dragons:
            for dragon in injured_dragons:
                self.create_dragon_card(injured_scroll, dragon)
        else:
            none_label = ctk.CTkLabel(
                injured_scroll,
                text="No dragons are currently injured.",
                font=("Arial", 13),
                text_color="#BDBDBD",
                justify="left"
            )
            none_label.pack(anchor="w", padx=8, pady=8)

        healer_title = ctk.CTkLabel(
            healer_frame,
            text="Available Healers",
            font=("Arial", 18, "bold"),
            text_color="#6FCF97"
        )
        healer_title.pack(anchor="w", padx=12, pady=(12, 6))

        healer_scroll = ctk.CTkScrollableFrame(healer_frame)
        healer_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        healers = [
            d for d in self.world.dragons
            if getattr(d, "status", "") == "Alive"
            and getattr(d, "role", "") == "Healer"
        ]

        if healers:
            for healer in healers:
                self.create_healer_card(healer_scroll, healer)
                
        else:
            none_label = ctk.CTkLabel(
                healer_scroll,
                text="No healers are currently available.",
                font=("Arial", 13),
                text_color="#BDBDBD",
                justify="left"
            )
            none_label.pack(anchor="w", padx=8, pady=8)

        close_btn = ctk.CTkButton(
            content,
            text="Return",
            width=140,
            command=self.destroy
        )
        close_btn.pack(pady=(0, 14))

    def create_dragon_card(self, parent, dragon):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", padx=6, pady=6)

        name = ctk.CTkLabel(
            card,
            text=f"{dragon.name}",
            font=("Arial", 15, "bold")
        )
        name.pack(anchor="w", padx=10, pady=(8, 2))

        assigned_healer = None
        if getattr(dragon, "assigned_healer_id", None) is not None:
            assigned_healer = next(
                (d for d in self.world.dragons if d.id == dragon.assigned_healer_id),
                None
            )

        assigned_text = assigned_healer.name if assigned_healer else "None"


        details = ctk.CTkLabel(
            card,
            text=(
                f"Tribe: {getattr(dragon, 'tribe', 'Unknown')}\n"
                f"Role: {getattr(dragon, 'role', 'Unknown')}\n"
                f"Health: {getattr(dragon, 'health', 'Unknown')}\n"
                f"Injured For: {getattr(dragon, 'injury_duration', 0)} moons\n"
                f"Assigned Healer: {assigned_text}\n" 
                f"Location: {getattr(dragon, 'location', 'Unknown')}"
            ),
            font=("Arial", 12),
            text_color="#6FCF97" if assigned_healer else "#EB5757",
            justify="left"
        )
        details.pack(anchor="w", padx=10, pady=(0, 8))


        has_healer = getattr(dragon, "assigned_healer_id", None) is not None

        if has_healer:
            assign_btn = ctk.CTkButton(
                parent,
                text="Healer Assigned",
                state="disabled"
            )
        else:
            assign_btn = ctk.CTkButton(
                card,
                text="Assign Healer",
                height=32,
                command=lambda d=dragon: self.open_assign_healer_window(d)
            )
        assign_btn.pack(fill="x", padx=10, pady=(0, 10))

    def open_assign_healer_window(self, injured_dragon):
        popup = ctk.CTkToplevel(self)
        popup.title(f"Assign Healer to {injured_dragon.name}")
        popup.geometry("420x360")

        popup.transient(self)
        popup.lift()
        popup.focus_force()
        popup.attributes("-topmost", True)
        popup.after(200, lambda: popup.attributes("-topmost", False))

        title = ctk.CTkLabel(
            popup,
            text=f"Assign healer to {injured_dragon.name}",
            font=("Arial", 18, "bold")
        )
        title.pack(pady=(18, 8))

        healers = [
            d for d in self.world.dragons
            if getattr(d, "status", "") == "Alive"
            and getattr(d, "role", "") == "Healer"
            and d.id != injured_dragon.id
        ]

        if not healers:
            msg = ctk.CTkLabel(
                popup,
                text="No healers are available.",
                font=("Arial", 13),
                text_color="#BDBDBD"
            )
            msg.pack(pady=20)
            return



        for healer in healers:
            assigned_count = sum(
                1 for d in self.world.dragons
                if getattr(d, "assigned_healer_id", None) == healer.id
            )

            if assigned_count >= 2:
                btn_text = f"{healer.name} ({healer.tribe}) - Full"
                btn_state = "disabled"
            else:
                btn_text = f"{healer.name} ({healer.tribe})"
                btn_state = "normal"

            btn = ctk.CTkButton(
                popup,
                text=btn_text,
                state=btn_state,
                command=lambda h=healer: self.assign_healer(injured_dragon, h, popup)
            )
            btn.pack(fill="x", padx=25, pady=6)

    def assign_healer(self, injured_dragon, healer, popup):
        injured_dragon.assigned_healer_id = healer.id

        popup.destroy()
        self.destroy()

        HealerDenWindow(self.parent, self.world)

    def create_healer_card(self, parent, healer):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", padx=6, pady=6)

        name = ctk.CTkLabel(
            card,
            text=f"{healer.name}",
            font=("Arial", 15, "bold")
        )
        name.pack(anchor="w", padx=10, pady=(8, 2))

        patient_count = sum(
            1 for d in self.world.dragons
            if getattr(d, "assigned_healer_id", None) == healer.id
        )

        details = ctk.CTkLabel(
            card,
            text=(
                f"Tribe: {getattr(healer, 'tribe', 'Unknown')}\n"
                f"Health: {getattr(healer, 'health', 'Unknown')}\n"
                f"Healer Skill: {getattr(healer, 'healer_skill', 1.0)}\n"
                f"Location: {getattr(healer, 'location', 'Unknown')}\n"
                f"Patients: {patient_count}/2\n"
            ),
            font=("Arial", 12),
            text_color="#BDBDBD",
            justify="left"
        )
        details.pack(anchor="w", padx=10, pady=(0, 8))