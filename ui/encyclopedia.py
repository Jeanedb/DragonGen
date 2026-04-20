import customtkinter as ctk

from core.sim.flavor import ensure_dragon_flavor, generate_dragon_bio
from core.sim.flavor import generate_legacy_text
from ui.dragon_panel import DragonPortraitPanel


class EncyclopediaWindow(ctk.CTkToplevel):
    def __init__(self, parent, world):
        super().__init__(parent)

        self.world = world
        self.selected_dragon = None
        self.dragon_buttons = []

        self.title("Dragon Encyclopedia")
        self.geometry("1200x800")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(0, weight=1)

        self.create_roster_panel()
        self.create_detail_panel()

        if self.world.dragons:
            self.selected_dragon = self.world.dragons[0]

        self.refresh_all()

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

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

    def create_roster_panel(self):
        self.roster_frame = ctk.CTkFrame(self)
        self.roster_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.filter_menu = ctk.CTkOptionMenu(
            self.roster_frame,
            values=["Living", "Dead", "All"],
            command=self.on_filter_changed
        )
        self.filter_menu.set("All")
        self.filter_menu.pack(fill="x", padx=8, pady=(8, 4))

        self.search_entry = ctk.CTkEntry(
            self.roster_frame,
            placeholder_text="Search dragon name..."
        )
        self.search_entry.pack(fill="x", padx=8, pady=(4, 8))
        self.search_entry.bind("<KeyRelease>", lambda event: self.refresh_roster())

        self.roster_scroll = ctk.CTkScrollableFrame(self.roster_frame)
        self.roster_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.current_filter = "All"

    def create_detail_panel(self):
        self.detail_frame = ctk.CTkFrame(self)
        self.detail_frame.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

        self.title_label = ctk.CTkLabel(
            self.detail_frame,
            text="Dragon Encyclopedia",
            font=("Arial", 20, "bold")
        )
        self.title_label.pack(anchor="w", padx=12, pady=(12, 6))

        self.portrait_panel = DragonPortraitPanel(self.detail_frame, width=320, height=440)
        self.portrait_panel.pack(fill="x", padx=12, pady=(0, 12))

        self.detail_text = ctk.CTkTextbox(self.detail_frame)
        self.detail_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    def on_filter_changed(self, choice):
        self.current_filter = choice
        self.refresh_roster()

    def get_dragon_by_id(self, dragon_id):
        for dragon in self.world.dragons:
            if dragon.id == dragon_id:
                return dragon
        return None

    def select_dragon(self, dragon):
        self.selected_dragon = dragon
        self.refresh_details()

    def refresh_all(self):
        for dragon in self.world.dragons:
            ensure_dragon_flavor(dragon)
        self.refresh_roster()
        self.refresh_details()

    def refresh_roster(self):
        for btn in self.dragon_buttons:
            btn.destroy()
        self.dragon_buttons.clear()

        search_text = self.search_entry.get().strip().lower()

        dragons = list(self.world.dragons)

        if self.current_filter == "Living":
            dragons = [d for d in dragons if d.status == "Alive"]
        elif self.current_filter == "Dead":
            dragons = [d for d in dragons if d.status == "Dead"]

        if search_text:
            dragons = [d for d in dragons if search_text in d.name.lower()]

        dragons.sort(key=lambda d: (d.status != "Alive", d.name.lower()))

        for dragon in dragons:
            style = self.get_tribe_button_style(dragon.tribe)

            if dragon.status == "Dead":
                style = {
                    "fg_color": "#444444",
                    "hover_color": "#555555",
                    "text_color": "#CCCCCC",
                }

            text = f"{dragon.name} ({dragon.tribe}) - {dragon.status}"
            btn = ctk.CTkButton(
                self.roster_scroll,
                text=text,
                anchor="w",
                command=lambda d=dragon: self.select_dragon(d),
                fg_color=style["fg_color"],
                hover_color=style["hover_color"],
                text_color=style["text_color"],
            )
            btn.pack(fill="x", padx=4, pady=2)
            self.dragon_buttons.append(btn)

    def refresh_details(self):
        self.detail_text.delete("1.0", "end")

        if not self.selected_dragon:
            return

        d = self.selected_dragon
        self.portrait_panel.set_dragon(d)
        ensure_dragon_flavor(d)

        bio_text = generate_dragon_bio(d, self.world)

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
        parents = [
            self.get_dragon_by_id(pid).name
            for pid in d.parents
            if self.get_dragon_by_id(pid)
        ]
        children = [
            self.get_dragon_by_id(cid).name
            for cid in d.dragonets
            if self.get_dragon_by_id(cid)
        ]

        legacy_text = generate_legacy_text(d, self.world) if d.status == "Dead" else ""

        mate_name = "None"
        if d.mate_id is not None:
            mate = self.get_dragon_by_id(d.mate_id)
            if mate:
                mate_name = mate.name

        friends_text = ", ".join(friends) if friends else "None"
        rivals_text = ", ".join(rivals) if rivals else "None"
        parents_text = ", ".join(parents) if parents else "Unknown"
        children_text = ", ".join(children) if children else "None"
        titles_text = ", ".join(d.earned_titles) if d.earned_titles else "None"
        hobbies_text = ", ".join(d.hobbies) if d.hobbies else "None"
        skills_text = ", ".join(d.skills) if d.skills else "None"
        scars_text = ", ".join(d.scars) if d.scars else "None"

        detail_block = (
            f"Name: {d.name}\n"
            f"Tribe: {d.tribe}\n"
            f"Age: {d.age_moons}\n"
            f"Role: {d.role}\n"
            f"Rank: {d.rank}\n"
            f"Personality: {d.personality}\n"
            f"Titles: {titles_text}\n"
            f"Health: {d.health}\n"
            f"Status: {d.status}\n"
            f"Height: {d.height:.1f} m\n"
            f"Eye Color: {d.eye_color}\n"
            f"Horn Type: {d.horn_type}\n"
            f"Head Type: {d.head_type}\n"
            f"Snout Type: {d.snout_type}\n"
            f"Eye Style: {d.eye_style}\n"
            f"Tail Type: {d.tail_type}\n"
            f"Leg Type: {d.leg_type}\n"
            f"Wing Type: {d.wing_type}\n"
            f"Body Type: {d.body_type}\n"
            f"Markings: {d.marking_type}\n"
            f"Scale Palette: {d.scale_palette}\n"
            f"Special Traits: {', '.join(d.special_visual_traits) if d.special_visual_traits else 'None'}\n"
            f"Skills: {skills_text}\n"
            f"Hobbies: {hobbies_text}\n"
            f"Scars: {scars_text}\n"
            f"Random Fact: {d.random_fact}\n\n"
            f"Friends: {friends_text}\n"
            f"Rivals: {rivals_text}\n"
            f"Mate: {mate_name}\n"
            f"Parents: {parents_text}\n"
            f"Dragonets: {children_text}\n\n"
            f"Biography:\n{bio_text}\n"
        )

        if legacy_text:
            detail_block += f"\nLegacy:\n{legacy_text}\n"

        self.detail_text.insert("end", detail_block)

        