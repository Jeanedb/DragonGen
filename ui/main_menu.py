import customtkinter as ctk
from game_main import run_game
import sys
import random
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

TRIBES = [
    ("skywing", "SkyWing", "Proud, fierce, and battle-ready."),
    ("seawing", "SeaWing", "Diplomatic, aquatic, and socially complex."),
    ("rainwing", "RainWing", "Colorful, emotional, and unpredictable."),
    ("sandwing", "SandWing", "Harsh, political, and survival-minded."),
    ("icewing", "IceWing", "Formal, hierarchical, and reputation-driven."),
    ("nightwing", "NightWing", "Secretive, clever, and prophecy-haunted."),
    ("mudwing", "MudWing", "Loyal, grounded, and family-focused."),
    ("mixed", "Mixed Tribe", "A varied tribe with unpredictable dynamics."),
]


class MainMenu(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DragonGen")
        self.geometry("900x780")
        self.minsize(800, 520)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.selected_tribe = None

        self.show_main_menu()

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()

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

    def show_main_menu(self):
        self.clear()
        self.set_background("assets/menu/main_menu_bg.png")

        # stronger shadow
        self.canvas.create_text(
            74, 109,
            text="DragonGen",
            anchor="nw",
            fill="#000000",
            font=("Arial", 56, "bold")
        )

        self.canvas.create_text(
            72, 107,
            text="DragonGen",
            anchor="nw",
            fill="#222222",
            font=("Arial", 56, "bold")
        )

        # main text
        self.canvas.create_text(
            70, 105,
            text="DragonGen",
            anchor="nw",
            fill="#EAD9A0",
            font=("Arial", 56, "bold")
        )

        self.canvas_menu_button(95, 340, "[NEW GAME]", self.show_tribe_selection)
        self.canvas_menu_button(95, 405, "[LOAD GAME]", self.load_game)
        self.canvas_menu_button(95, 470, "[OPTIONS]", self.show_options)
        self.canvas_menu_button(95, 535, "[EXIT]", self.destroy)

    def canvas_menu_button(self, x, y, text, command):
        shadow = self.canvas.create_text(
            x+2, y+2,
            text=text,
            anchor="nw",
            fill="#000000",
            font=("Arial", 30, "bold")
        )

        item = self.canvas.create_text(
            x, y,
            text=text,
            anchor="nw",
            fill="#EAD9A0",
            font=("Arial", 30, "bold")
        )

        def on_enter(event):
            self.canvas.itemconfig(item, fill="#FFF4CC")

        def on_leave(event):
            self.canvas.itemconfig(item, fill="#EAD9A0")

        def on_click(event):
            command()

        self.canvas.tag_bind(item, "<Enter>", on_enter)
        self.canvas.tag_bind(item, "<Leave>", on_leave)
        self.canvas.tag_bind(item, "<Button-1>", on_click)

    def menu_button(self, parent, text, command):
        btn = ctk.CTkButton(
            parent,
            text=f"[{text.upper()}]",
            command=command,
            fg_color="transparent",
            hover_color="#3A2A1A",
            text_color="#F6DFA8",
            font=("Arial", 30, "bold"),
            width=260,
            height=48,
            anchor="w"
        )
        btn.pack(anchor="w", pady=6)


    def show_tribe_selection(self):
        self.clear()
        
    

        title = ctk.CTkLabel(
            self,
            text="Choose Your Tribe",
            font=("Arial", 32, "bold")
        )
        title.pack(pady=(28, 5))

        subtitle = ctk.CTkLabel(
            self,
            text="Your choice will shape how your tribe behaves, forms bonds, and faces conflict.",
            font=("Arial", 13),
            text_color="#BDBDBD"
        )
        subtitle.pack(pady=(0, 18))

        grid = ctk.CTkFrame(self)
        grid.pack(fill="both", expand=False, padx=25, pady=10)

        for col in range(2):
            grid.grid_columnconfigure(col, weight=1)

        for idx, (tribe_id, name, desc) in enumerate(TRIBES):
            is_selected = self.selected_tribe == tribe_id

            row = idx // 2
            col = idx % 2

            card = ctk.CTkFrame(
                grid,
                corner_radius=12,
                fg_color="#2F4F6F" if is_selected else None,
                border_width=2 if is_selected else 0,
                border_color="#4A90E2"
            )
            card.grid(row=row, column=col, sticky="nsew", padx=8, pady=6)

            label = ctk.CTkLabel(
                card,
                text=name,
                font=("Arial", 18, "bold")
            )
            label.pack(anchor="w", padx=16, pady=(10, 2))

            blurb = ctk.CTkLabel(
                card,
                text=desc,
                font=("Arial", 12),
                text_color="#BDBDBD",
                wraplength=340,
                justify="left"
            )
            blurb.pack(anchor="w", padx=16, pady=(0, 8))

            btn = ctk.CTkButton(
                card,
                text="Selected" if is_selected else f"Select {name}",
                height=36,
                command=lambda tid=tribe_id: self.select_tribe(tid)
            )
            btn.pack(fill="x", padx=16, pady=(0, 10))

        bottom_area = ctk.CTkFrame(self, fg_color="transparent")
        bottom_area.pack(fill="x", padx=25, pady=(6, 14))

        summary = ctk.CTkFrame(bottom_area)
        summary.pack(side="left", fill="x", expand=True, padx=(0, 12))

        if self.selected_tribe:
            selected_name = next(name for tid, name, _ in TRIBES if tid == self.selected_tribe)
            selected_desc = next(desc for tid, _, desc in TRIBES if tid == self.selected_tribe)

            summary_title = ctk.CTkLabel(
                summary,
                text=f"Selected Tribe: {selected_name}",
                font=("Arial", 16, "bold")
            )
            summary_title.pack(anchor="w", padx=12, pady=(6, 0))

            summary_desc = ctk.CTkLabel(
                summary,
                text=selected_desc,
                font=("Arial", 12),
                text_color="#BDBDBD"
            )
            summary_desc.pack(anchor="w", padx=12, pady=(0, 6))
        else:
            summary_title = ctk.CTkLabel(
                summary,
                text="Select a tribe to continue.",
                font=("Arial", 16, "bold")
            )
            summary_title.pack(anchor="w", padx=12, pady=10)

        button_area = ctk.CTkFrame(bottom_area, fg_color="transparent")
        button_area.pack(side="right")

        begin_btn = ctk.CTkButton(
            button_area,
            text="Begin Tribe",
            width=160,
            height=40,
            font=("Arial", 14, "bold"),
            command=self.confirm_start,
            state="normal" if self.selected_tribe else "disabled"
        )
        begin_btn.pack(side="left", padx=6)

        back_btn = ctk.CTkButton(
            button_area,
            text="Back",
            width=110,
            height=40,
            command=self.show_main_menu
        )
        back_btn.pack(side="left", padx=6)

    def select_tribe(self, tribe_id):
        self.selected_tribe = tribe_id
        self.show_tribe_selection()  # re-render UI

    def confirm_start(self):
        if not self.selected_tribe:
            return

        self.show_launching_screen()

    def show_launching_screen(self):
        self.clear()

        selected_name = next(
            name for tid, name, _ in TRIBES
            if tid == self.selected_tribe
        )

        self.loading_text = ctk.CTkLabel(
            self,
            text=f"Preparing the {selected_name}...",
            font=("Arial", 32, "bold")
        )
        self.loading_text.pack(pady=(180, 12))

        self.subtext = ctk.CTkLabel(
            self,
            text="",
            font=("Arial", 15),
            text_color="#BDBDBD"
        )
        self.subtext.pack(pady=(0, 20))

        self.progress = ctk.CTkProgressBar(self, width=360)
        self.progress.pack(pady=10)
        self.progress.set(0)

        self.loading_steps = [
            "Gathering dragons...",
            "Assigning roles...",
            "Establishing hierarchy...",
            "Finalizing tribe..."
        ]

        self.current_step = 0

        self.run_loading_sequence()

    def run_loading_sequence(self):
        if self.current_step < len(self.loading_steps):
            text = self.loading_steps[self.current_step]
            self.subtext.configure(text=text)

            progress_value = (self.current_step + 1) / len(self.loading_steps)
            self.animate_progress(progress_value)

            self.current_step += 1

            self.after(random.randint(250, 450), self.run_loading_sequence)
        else:
            self.after(200, self.launch_selected_tribe)

    def animate_progress(self, target):
        current = self.progress.get()
        step = (target - current) / 10

        def step_progress():
            nonlocal current
            if abs(target - current) < 0.01:
                self.progress.set(target)
                return
            current += step
            self.progress.set(current)
            self.after(30, step_progress)

        step_progress()

    def launch_selected_tribe(self):
        selected = self.selected_tribe
        self.destroy()
        run_game(selected)


    def load_game(self):
        self.destroy()
        run_game("mixed")
        
    def show_options(self):
        self.clear()

        title = ctk.CTkLabel(
            self,
            text="Options",
            font=("Arial", 30, "bold")
        )
        title.pack(pady=(80, 10))

        body = ctk.CTkLabel(
            self,
            text="Options will go here later.",
            font=("Arial", 14),
            text_color="#BDBDBD"
        )
        body.pack(pady=10)

        back_btn = ctk.CTkButton(
            self,
            text="Back",
            width=160,
            command=self.show_main_menu
        )
        back_btn.pack(pady=30)