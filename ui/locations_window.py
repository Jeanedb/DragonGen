import customtkinter as ctk

from ui.conversation_panel import ConversationPanel
from ui.tribal_relations import TribalRelationsWindow
from core.sim.locations import get_location_name
from core.sim.location_utils import get_dragons_here_text
from ui.encyclopedia import EncyclopediaWindow
from ui.healer_den import HealerDenWindow


class LocationsWindow(ctk.CTkToplevel):

    def get_dragons_here_text(world, loc_id):
        dragons_here = [
            d for d in world.dragons
            if d.status == "Alive" and getattr(d, "location", None) == loc_id
        ]

        if not dragons_here:
            return "No dragons are currently here."

        return "\n".join(
            f"- {d.name} ({d.role})"
            for d in dragons_here
        )

    def __init__(self, parent, world):
        super().__init__(parent)

        self.parent = parent
        self.world = world

        self.title("Locations")
        self.geometry("650x520")

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self.create_layout()


    def create_layout(self):
        title = ctk.CTkLabel(
            self,
            text="Tribe Locations",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=(15, 5))

        subtitle = ctk.CTkLabel(
            self,
            text="Choose where to focus your attention this week.",
            font=("Arial", 13),
            text_color="#BDBDBD"
        )
        subtitle.pack(pady=(0, 12))

        self.grid = ctk.CTkFrame(self)
        self.grid.pack(fill="both", expand=True, padx=15, pady=10)

        locations = [
            ("village_center", "Open conversations and social interactions", self.open_village_center),
            ("queen_palace", "Review diplomacy and tribal relations", self.open_queen_palace),
            ("healer_den", "Healing, injuries, and recovery", self.open_healer_den),
            ("training_grounds", "Training, sparring, and warrior activity", self.open_placeholder),
            ("hunting_grounds", "Hunting and resource activity", self.open_placeholder),
            ("border_routes", "Patrols, border incidents, and outside threats", self.open_placeholder),
            ("scroll_library", "History, knowledge, and records", self.open_scroll_library),
            ("hatchery", "Dragonets, families, and future generations", self.open_placeholder),
        ]

        for idx, (loc_id, desc, command) in enumerate(locations):
            row = idx // 2
            col = idx % 2

            card = ctk.CTkFrame(self.grid, corner_radius=12)
            card.grid(row=row, column=col, sticky="nsew", padx=8, pady=8)

            self.grid.grid_columnconfigure(col, weight=1)

            count = self.get_location_count(loc_id)

            name = ctk.CTkLabel(
                card,
                text=f"{get_location_name(loc_id)} ({count})",
                font=("Arial", 15, "bold")
            )
            name.pack(anchor="w", padx=12, pady=(10, 2))

            blurb = ctk.CTkLabel(
                card,
                text=desc,
                font=("Arial", 12),
                text_color="#BDBDBD",
                wraplength=260,
                justify="left"
            )
            blurb.pack(anchor="w", padx=12, pady=(0, 8))

            btn = ctk.CTkButton(
                card,
                text="Enter",
                command=lambda loc_id=loc_id, command=command: command(loc_id)
            )
            btn.pack(fill="x", padx=12, pady=(0, 12))

    def open_healer_den(self, loc_id):
        HealerDenWindow(self, self.world)

    def open_scroll_library(self, loc_id):
        EncyclopediaWindow(self.parent, self.world)

    def open_village_center(self, loc_id):
        ConversationPanel(self.parent, self.world)

    def open_queen_palace(self, loc_id):
        TribalRelationsWindow(self.parent, self.world)

    def open_placeholder(self, loc_id):
        PlaceholderLocationWindow(self, self.world, loc_id)

    def get_location_count(self, loc_id):
        return sum(
            1 for d in self.world.dragons
            if getattr(d, "status", "") == "Alive"
            and getattr(d, "location", "") == loc_id
        )


class PlaceholderLocationWindow(ctk.CTkToplevel):
    def __init__(self, parent, world, loc_id):
        super().__init__(parent)

        self.world = world
        self.loc_id = loc_id

        self.title(get_location_name(loc_id))
        self.geometry("450x300")

        title = ctk.CTkLabel(
            self,
            text=get_location_name(loc_id),
            font=("Arial", 18, "bold")
        )
        title.pack(pady=(20, 8))

        dragons_here = [
            d for d in world.dragons
            if d.status == "Alive" and getattr(d, "location", None) == loc_id
        ]

        if dragons_here:
            dragon_text = "\n".join(
                f"- {d.name} ({d.role})"
                for d in dragons_here
            )
        else:
            dragon_text = "No dragons are currently here."

        body = ctk.CTkLabel(
            self,
            text=f"Dragons currently here:\n\n{dragon_text}",
            font=("Arial", 13),
            justify="left",
            wraplength=380
        )
        body.pack(padx=20, pady=10)