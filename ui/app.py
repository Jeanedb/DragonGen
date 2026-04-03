import customtkinter as ctk
from tkinter import filedialog

from data.tribes import TRIBES
from core.generator import generate_starting_world
from core.simulation import advance_moon, resolve_choice
from core.save_manager import save_world, load_world

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DragonGenApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DragonGen")
        self.geometry("1100x750")

        # Game state
        self.selected_tribe = "Mixed"
        self.world = generate_starting_world(self.selected_tribe)
        self.selected_dragon = self.world.dragons[0] if self.world.dragons else None

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=2)
        self.grid_rowconfigure(0, weight=0)   # header
        self.grid_rowconfigure(1, weight=1)   # main content
        self.grid_rowconfigure(2, weight=0)   # choice
        self.grid_rowconfigure(3, weight=0)   # controls

        self.create_header()
        self.create_roster_panel()
        self.create_detail_panel()
        self.create_event_log()
        self.create_choice_panel()
        self.create_controls()

        self.refresh_all()

    def create_header(self):
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, columnspan=3, sticky="ew", padx=5, pady=5)

        self.header_label = ctk.CTkLabel(
            self.header_frame,
            text="",
            font=("Arial", 18, "bold")
        )
        self.header_label.pack(padx=10, pady=(10, 5))

        self.tribe_selector = ctk.CTkOptionMenu(
            self.header_frame,
            values=["Mixed"] + TRIBES,
            command=self.on_tribe_selected
        )
        self.tribe_selector.set("Mixed")
        self.tribe_selector.pack(pady=(0, 10))

    def create_roster_panel(self):
        self.roster_frame = ctk.CTkFrame(self)
        self.roster_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.roster_scroll = ctk.CTkScrollableFrame(self.roster_frame)
        self.roster_scroll.pack(fill="both", expand=True)

        self.dragon_buttons = []

    def create_detail_panel(self):
        self.detail_frame = ctk.CTkFrame(self)
        self.detail_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        self.detail_text = ctk.CTkTextbox(self.detail_frame)
        self.detail_text.pack(fill="both", expand=True)

    def create_event_log(self):
        self.event_frame = ctk.CTkFrame(self)
        self.event_frame.grid(row=1, column=2, sticky="nsew", padx=5, pady=5)

        self.event_text = ctk.CTkTextbox(self.event_frame)
        self.event_text.pack(fill="both", expand=True)

    def create_choice_panel(self):
        self.choice_frame = ctk.CTkFrame(self)
        self.choice_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=5, pady=5)

        self.choice_label = ctk.CTkLabel(
            self.choice_frame,
            text="",
            wraplength=1000,
            justify="left",
            font=("Arial", 14, "bold")
        )
        self.choice_label.pack(padx=10, pady=(10, 5), anchor="w")

        self.choice_buttons_frame = ctk.CTkFrame(self.choice_frame)
        self.choice_buttons_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.choice_buttons = []

    def create_controls(self):
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=3, column=0, columnspan=3, sticky="ew", padx=5, pady=5)

        self.advance_button = ctk.CTkButton(
            self.control_frame,
            text="Advance Moon",
            command=self.on_advance_moon
        )
        self.advance_button.pack(side="left", padx=10, pady=10)

        self.save_button = ctk.CTkButton(
            self.control_frame,
            text="Save",
            command=self.on_save
        )
        self.save_button.pack(side="left", padx=10, pady=10)

        self.load_button = ctk.CTkButton(
            self.control_frame,
            text="Load",
            command=self.on_load
        )
        self.load_button.pack(side="left", padx=10, pady=10)

        self.new_button = ctk.CTkButton(
            self.control_frame,
            text="New Tribe",
            command=self.on_new_tribe
        )
        self.new_button.pack(side="left", padx=10, pady=10)

    def on_tribe_selected(self, choice):
        self.selected_tribe = choice

    def on_new_tribe(self):
        self.world = generate_starting_world(self.selected_tribe)
        self.selected_dragon = self.world.dragons[0] if self.world.dragons else None
        self.refresh_all()

    def on_advance_moon(self):
        if self.world.pending_choice is not None:
            self.refresh_choice_panel()
            return

        advance_moon(self.world)
        self.refresh_all()

    def on_save(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialdir="saves"
        )
        if filename:
            save_world(self.world, filename)

    def on_load(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json")],
            initialdir="saves"
        )
        if filename:
            self.world = load_world(filename)
            self.selected_dragon = self.world.dragons[0] if self.world.dragons else None
            self.refresh_all()

    def on_choice_selected(self, option_id):
        resolve_choice(self.world, option_id)
        self.refresh_all()

    def get_dragon_by_id(self, dragon_id):
        for dragon in self.world.dragons:
            if dragon.id == dragon_id:
                return dragon
        return None

    def select_dragon(self, dragon):
        self.selected_dragon = dragon
        self.refresh_details()

    def refresh_all(self):
        self.refresh_header()
        self.refresh_roster()
        self.refresh_details()
        self.refresh_events()
        self.refresh_choice_panel()

    def refresh_header(self):
        living_count = sum(1 for d in self.world.dragons if d.status == "Alive")
        dead_count = sum(1 for d in self.world.dragons if d.status == "Dead")

        self.header_label.configure(
            text=(
                f"Tribe: {self.world.tribe_name}    |    "
                f"Moon: {self.world.moon}    |    "
                f"Living: {living_count}    |    "
                f"Dead: {dead_count}"
            )
        )

    def refresh_roster(self):
        for btn in self.dragon_buttons:
            btn.destroy()
        self.dragon_buttons.clear()

        for d in self.world.dragons:
            btn = ctk.CTkButton(
                self.roster_scroll,
                text=f"{d.name} ({d.tribe}) - {d.role} [{d.rank}] - {d.status}",
                anchor="w",
                command=lambda dragon=d: self.select_dragon(dragon)
            )
            btn.pack(fill="x", padx=5, pady=2)
            self.dragon_buttons.append(btn)

    def refresh_details(self):
        self.detail_text.delete("1.0", "end")

        if not self.world.dragons:
            return

        d = self.selected_dragon or self.world.dragons[0]

        friends = [
            self.get_dragon_by_id(fid).name
            for fid in d.friends
            if self.get_dragon_by_id(fid)
        ]
        rivals = [
            self.get_dragon_by_id(rid).name
            for rid in d.rivals
            if self.get_dragon_by_id(rid)
        ]
        parent_names = [
            self.get_dragon_by_id(pid).name
            for pid in d.parents
            if self.get_dragon_by_id(pid)
        ]
        child_names = [
            self.get_dragon_by_id(cid).name
            for cid in d.dragonets
            if self.get_dragon_by_id(cid)
        ]

        friends_text = ", ".join(friends) if friends else "None"
        rivals_text = ", ".join(rivals) if rivals else "None"
        parents_text = ", ".join(parent_names) if parent_names else "Unknown"
        children_text = ", ".join(child_names) if child_names else "None"

        personal_events = []
        for event in self.world.event_log:
            if isinstance(event, dict) and d.id in event.get("involved_ids", []):
                text = event.get("text", "")
                importance = event.get("importance", 1)

                if importance >= 4:
                    text = f"⭐ {text}"

                personal_events.append(text)

            elif isinstance(event, str) and d.name in event:
                personal_events.append(event)

        personal_history_text = (
            "\n".join(personal_events[-8:])
            if personal_events else
            "No personal history yet."
        )

        self.detail_text.insert(
            "end",
            f"Name: {d.name}\n"
            f"Tribe: {d.tribe}\n"
            f"Age: {d.age_moons}\n"
            f"Role: {d.role}\n"
            f"Rank: {d.rank}\n"
            f"Personality: {d.personality}\n"
            f"Health: {d.health}\n"
            f"Status: {d.status}\n\n"
            f"Friends: {friends_text}\n"
            f"Rivals: {rivals_text}\n"
            f"Parents: {parents_text}\n"
            f"Dragonets: {children_text}\n\n"
            f"Recent Personal History:\n{personal_history_text}\n"
        )

    def refresh_events(self):
        self.event_text.delete("1.0", "end")

        for event in self.world.event_log[-20:]:
            if isinstance(event, dict):
                text = event.get("text", "")
            else:
                text = str(event)

            self.event_text.insert("end", f"- {text}\n")

    def refresh_choice_panel(self):
        for btn in self.choice_buttons:
            btn.destroy()
        self.choice_buttons.clear()

        choice = self.world.pending_choice

        if not choice:
            self.choice_label.configure(text="No current decision.")
            return

        self.choice_label.configure(text=choice.get("text", ""))

        for option in choice.get("options", []):
            btn = ctk.CTkButton(
                self.choice_buttons_frame,
                text=option["text"],
                command=lambda option_id=option["id"]: self.on_choice_selected(option_id)
            )
            btn.pack(side="left", padx=10, pady=5)
            self.choice_buttons.append(btn)