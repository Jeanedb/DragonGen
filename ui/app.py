import customtkinter as ctk
from tkinter import filedialog

from data.tribes import TRIBES
from core.generator import generate_starting_world
from core.simulation import (
    advance_moon,
    resolve_choice,
    get_world_mood,
    get_tribe_climate,
)
from core.save_manager import save_world, load_world
from core.sim.leadership import maintain_hierarchy

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
        maintain_hierarchy(self.world)
        self.selected_dragon = self.world.dragons[0] if self.world.dragons else None
        self.roster_filter = "Living"

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

        # Tribe Status Panel
        self.status_frame = ctk.CTkFrame(self.header_frame)
        self.status_frame.pack(fill="x", padx=10, pady=(0, 6))

        # Top line: Title + Tension
        self.status_top_row = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        self.status_top_row.pack(fill="x", padx=10, pady=(4, 2))

        self.status_title = ctk.CTkLabel(
            self.status_top_row,
            text="Tribe Status",
            font=("Arial", 13, "bold")
        )
        self.status_title.pack(side="left")

        self.tension_value_label = ctk.CTkLabel(
            self.status_top_row,
            text="Tension: 0.0 / 5.0",
            font=("Arial", 12)
        )
        self.tension_value_label.pack(side="left", padx=(15, 0))

        # Bar
        self.tension_bar = ctk.CTkProgressBar(self.status_frame, height=10)
        self.tension_bar.pack(fill="x", padx=10, pady=(0, 3))
        self.tension_bar.set(0)

        # Mood
        self.tension_status_label = ctk.CTkLabel(
            self.status_frame, text="Mood: Calm", font=("Arial", 12, "bold")
        )
        self.tension_status_label.pack(anchor="w", padx=10, pady=(0, 1))


        # Blurb (kept, but tighter)
        self.tension_desc_label = ctk.CTkLabel(
            self.status_frame,
            text="The tribe feels steady and cooperative.",
            font=("Arial", 12),
            wraplength=1000,
            justify="left"
        )
        self.tension_desc_label.pack(anchor="w", padx=10, pady=(0, 6))

    def create_roster_panel(self):
        self.roster_frame = ctk.CTkFrame(self)
        self.roster_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.roster_filter_menu = ctk.CTkOptionMenu(
            self.roster_frame,
            values=["Living", "All", "Dead"],
            command=self.on_roster_filter_changed
        )
        self.roster_filter_menu.set("Living")
        self.roster_filter_menu.pack(fill="x", padx=5, pady=(5, 0))

        self.roster_scroll = ctk.CTkScrollableFrame(self.roster_frame)
        self.roster_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        self.dragon_buttons = []

    def on_roster_filter_changed(self, choice):
        self.roster_filter = choice
        self.refresh_roster()

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
            text="No current decision.",
            wraplength=1000,
            justify="left",
            font=("Arial", 12)
        )
        self.choice_label.pack(padx=10, pady=(6, 6), anchor="w")

        self.choice_buttons_frame = ctk.CTkFrame(self.choice_frame)
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
        maintain_hierarchy(self.world)
        self.selected_dragon = self.world.dragons[0] if self.world.dragons else None
        self.roster_filter = "Living"
        self.roster_filter_menu.set("Living")
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
            maintain_hierarchy(self.world)
            self.selected_dragon = self.world.dragons[0] if self.world.dragons else None
            self.roster_filter = "Living"
            self.roster_filter_menu.set("Living")
            self.refresh_all()

    def on_choice_selected(self, option_id):
        resolve_choice(self.world, option_id)
        self.refresh_all()

    def get_dragon_by_id(self, dragon_id):
        for dragon in self.world.dragons:
            if dragon.id == dragon_id:
                return dragon
        return None

    def get_tension_status(self):
        tension = getattr(self.world, "tension", 0.0)

        if tension < 0.75:
            return "Calm", "The tribe feels steady and cooperative."
        elif tension < 1.5:
            return "Uneasy", "Small frictions are starting to show."
        elif tension < 2.5:
            return "Strained", "Conflict is affecting daily life in the tribe."
        elif tension < 3.5:
            return "Volatile", "Tensions are high and conflict feels close."
        else:
            return "Crisis", "The tribe is on edge and stability is slipping."

    def get_tribe_button_style(self, tribe):
        styles = {
            "MudWing": {
                "fg_color": "#6B4F3A",
                "hover_color": "#7A5A42", 
                "text_color": "#F5E6D3",
            },
            "NightWing": {
                "fg_color": "#2C2238",
                "hover_color": "#3A2B4A",
                "text_color": "#E8DDF5",
            },
            "SkyWing": {
                "fg_color": "#8B2E1E",
                "hover_color": "#A33824",
                "text_color": "#FFE7E0",
            },
            "IceWing": {
                "fg_color": "#6FAFCF",
                "hover_color": "#80BDD9",
                "text_color": "#0F2230",
            },
            "SandWing": {
                "fg_color": "#B08A3E",
                "hover_color": "#C49A45",
                "text_color": "#2C2212",
            },
            "SeaWing": {
                "fg_color": "#1F5D73",
                "hover_color": "#2A7088",
                "text_color": "#DFF6FF",
            },
            "RainWing": {
                "fg_color": "#3E8B4A",
                "hover_color": "#4BA85A",
                "text_color": "#E8FFE8",
            },
            "HiveWing": {
                "fg_color": "#7A5C1B",
                "hover_color": "#8C6A20",
                "text_color": "#FFF4CC",
            },
            "SilkWing": {
                "fg_color": "#8C5FA8",
                "hover_color": "#9E6DBD",
                "text_color": "#F6ECFF",
            },
            "LeafWing": {
                "fg_color": "#3F6B2F",
                "hover_color": "#4C8038",
                "text_color": "#E9F7E1",
            },
        }

        return styles.get(
            tribe,
            {
                "fg_color": "#2B5D8A",
                "hover_color": "#3673A8",
                "text_color": "#FFFFFF",
            }
        )

    def select_dragon(self, dragon):
        self.selected_dragon = dragon
        self.refresh_details()

    def refresh_all(self):
        self.refresh_header()
        self.refresh_status()
        self.refresh_roster()
        self.refresh_details()
        self.refresh_events()
        self.refresh_choice_panel()

    def refresh_status(self):
        tension = getattr(self.world, "tension", 0.0)
        clamped_tension = max(0.0, min(5.0, tension))

        mood = get_world_mood(self.world)
        climate = get_tribe_climate(self.world)
        leader = getattr(self.world, "leader", None)

        # Base mood description
        _, description = self.get_tension_status()
 
        # Leader text
        if leader:
            traits = getattr(leader, "personality_traits", []) or []
            if traits:
                leader_text = f"Leader: {leader.name} ({', '.join(traits)})"
            else:
                leader_text = f"Leader: {leader.name}"
        else:
            leader_text = "Leader: None"

        # Climate overlay on description
        if climate["suspicion_bias"] > 0.25:
            description += " Trust feels thin."
        elif climate["recovery_bias"] > 0.25:
            description += " The tribe still seems to be holding together."
        elif climate["conflict_bias"] > 0.30:
            description += " Conflict seems to surface easily."

        self.tension_value_label.configure(
            text=f"Tension: {clamped_tension:.1f} / 5.0"
        )
        self.tension_bar.set(clamped_tension / 5.0)
        self.tension_status_label.configure(text=f"Mood: {mood}")
        self.tension_desc_label.configure(text=description)

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

        if self.roster_filter == "Living":
            dragons_to_show = [d for d in self.world.dragons if d.status == "Alive"]
        elif self.roster_filter == "Dead":
            dragons_to_show = [d for d in self.world.dragons if d.status == "Dead"]
        else:
            dragons_to_show = list(self.world.dragons)

        for d in dragons_to_show:
            style = self.get_tribe_button_style(d.tribe)

            btn = ctk.CTkButton(
                self.roster_scroll,
                text=f"{d.name} ({d.tribe}) - {d.role} [{d.rank}] - {d.status}",
                anchor="w",
                command=lambda dragon=d: self.select_dragon(dragon),
                fg_color=style["fg_color"],
                hover_color=style["hover_color"],
                text_color=style["text_color"],
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
        memory_lines = []

        for flag, other_id in d.memory_flags:
            other = self.get_dragon_by_id(other_id)
            if not other:
                continue

            if flag == "saved_by":
                trust_value = d.trust.get(other.id, 0)

                if trust_value >= 4:
                    memory_lines.append(
                        f"Deeply trusts {other.name}, remembering when they stood by them in a moment of danger."
                    )
                else:
                    memory_lines.append(
                        f"Still trusts {other.name} after they stood by them in a moment of danger."
                    )

            elif flag == "abandoned_by":
                resentment_value = d.resentment.get(other.id, 0)

                if resentment_value >= 4:
                    memory_lines.append(
                        f"Holds a deep grudge against {other.name} for abandoning them when it mattered."
                    )
                else:
                    memory_lines.append(
                        f"Has never quite forgiven {other.name} for leaving when it mattered."
                    )

            elif flag == "lost_mate":
                other = self.get_dragon_by_id(other_id)
                if other:
                    # how long ago did they die (approximation)
                    time_since_loss = d.age_moons - other.age_moons

                    if time_since_loss < 10:
                        memory_lines.append(
                            f"The loss of {other.name} is still fresh, and it shows."
                        )
                    else:
                        memory_lines.append(
                            f"Still carries the memory of losing {other.name}, though time has dulled the edge."
                        )

        memory_text = "\n".join(memory_lines) if memory_lines else "None"

        child_names = [
            self.get_dragon_by_id(cid).name
            for cid in d.dragonets
            if self.get_dragon_by_id(cid)
        ]
        mate_name = "None"
        if d.mate_id is not None:
            mate = self.get_dragon_by_id(d.mate_id)
            if mate:
                mate_name = mate.name

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
            f"Mate: {mate_name}\n"
            f"Parents: {parents_text}\n"
            f"Dragonets: {children_text}\n\n"
            f"Notable Personal History:\n{memory_text}\n\n"
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
            self.choice_label.configure(text="No current decision.", font=("Arial", 12))
            self.choice_buttons_frame.pack_forget()
            return

        self.choice_label.configure(
            text=choice.get("text", ""),
            font=("Arial", 14, "bold")
        )

        if not self.choice_buttons_frame.winfo_ismapped():
            self.choice_buttons_frame.pack(fill="x", padx=10, pady=(0, 10))

        for option in choice.get("options", []):
            btn = ctk.CTkButton(
                self.choice_buttons_frame,
                text=option["text"],
                command=lambda option_id=option["id"]: self.on_choice_selected(option_id)
            )
            btn.pack(side="left", padx=10, pady=5)
            self.choice_buttons.append(btn)