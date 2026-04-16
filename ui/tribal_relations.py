import customtkinter as ctk
from core.sim.politics import get_relation_status
from data.tribe_profiles import TRIBE_PROFILES
from core.generator import generate_starting_world


class TribalRelationsWindow(ctk.CTkToplevel):

    def __init__(self, parent, world):
        super().__init__(parent)

        self.world = world
        self.selected_tribe = None
        self.tribe_buttons = []
        self.previous_tribal_relations = {}

        self.title("Tribal Relations")
        self.geometry("1000x700")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self.create_roster_panel()
        self.create_detail_panel()

        if self.world.tribal_relations:
            self.selected_tribe = sorted(self.world.tribal_relations.keys())[0]

        self.refresh_all()

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

    def get_relation_trend(self, tribe):
        current = self.world.tribal_relations.get(tribe, 0)
        previous = getattr(self.world, "previous_tribal_relations", {}).get(tribe, current)

        if current > previous:
            return "↑ Improving"
        elif current < previous:
            return "↓ Worsening"
        else:
            return "→ Stable"

    def create_roster_panel(self):
        self.left_frame = ctk.CTkFrame(self)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        self.title_label = ctk.CTkLabel(
            self.left_frame,
            text="Tribes",
            font=("Arial", 18, "bold")
        )
        self.title_label.pack(anchor="w", padx=10, pady=(10, 6))

        self.tribe_scroll = ctk.CTkScrollableFrame(self.left_frame)
        self.tribe_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def apply_policy(self, action_id):
        if not self.selected_tribe:
            return

        # fake a pending choice structure
        self.world.pending_choice = {
            "type": "tribal_policy_choice",
            "tribe": self.selected_tribe
        }

        from core.sim.choices import resolve_choice
        resolve_choice(self.world, action_id)

        self.refresh_all()

    def create_detail_panel(self):
        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

        self.detail_title = ctk.CTkLabel(
            self.right_frame,
            text="Relation Details",
            font=("Arial", 20, "bold")
        )
        self.detail_title.pack(anchor="w", padx=12, pady=(12, 6))

        self.detail_text = ctk.CTkTextbox(self.right_frame)
        self.detail_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.action_frame = ctk.CTkFrame(self.right_frame)
        self.action_frame.pack(fill="x", padx=12, pady=(0, 12))

        self.peace_btn = ctk.CTkButton(
            self.action_frame,
            text="Send Peace Gesture",
            command=lambda: self.apply_policy("peace_gesture")
        )
        self.peace_btn.pack(side="left", padx=5)

        self.patrol_btn = ctk.CTkButton(
            self.action_frame,
            text="Border Patrol",
            command=lambda: self.apply_policy("border_patrol")
        )
        self.patrol_btn.pack(side="left", padx=5)

        self.pressure_btn = ctk.CTkButton(
            self.action_frame,
            text="Apply Pressure",
            command=lambda: self.apply_policy("border_pressure")
        )
        self.pressure_btn.pack(side="left", padx=5)

        self.aid_btn = ctk.CTkButton(
            self.action_frame,
            text="Offer Aid",
            command=lambda: self.apply_policy("offer_aid")
        )
        self.aid_btn.pack(side="left", padx=5)

    def select_tribe(self, tribe):
        self.selected_tribe = tribe
        self.refresh_details()

    def get_relation_description(self, score):
        status = get_relation_status(score)

        if status == "War":
            return "Relations are effectively at war. Hostile incidents and violent encounters would be highly likely."
        elif status == "Hostile":
            return "Relations are openly hostile. Border incidents, suspicion, and conflict are more likely."
        elif status == "Uneasy":
            return "Relations are strained and uncertain. Trust is limited, and tensions could worsen."
        elif status == "Neutral":
            return "Relations are currently neutral. Neither openly friendly nor openly hostile."
        elif status == "Friendly":
            return "Relations are positive. Cooperation, peaceful contact, or softer encounters are more likely."
        elif status == "Allied":
            return "Relations are very strong. Mutual trust and support would be expected."
        return "No description available."

    def get_regions_for_tribe(self, tribe):
        return [
            region_name
            for region_name, owner in self.world.territory_control.items()
            if owner == tribe
        ]

    def refresh_all(self):
        self.refresh_roster()
        self.refresh_details()

    def refresh_roster(self):
        for btn in self.tribe_buttons:
            btn.destroy()
        self.tribe_buttons.clear()

        for tribe in sorted(self.world.tribal_relations.keys()):
            score = self.world.tribal_relations[tribe]
            status = get_relation_status(score)
            trend = self.get_relation_trend(tribe)


            btn = ctk.CTkButton(
                self.tribe_scroll,
                text=f"{tribe} — {status} ({score}) {trend}",
                anchor="w",
                command=lambda t=tribe: self.select_tribe(t)
            )
            btn.pack(fill="x", padx=4, pady=2)
            self.tribe_buttons.append(btn)

    def refresh_details(self):
        self.detail_text.delete("1.0", "end")

        if not self.selected_tribe:
            self.detail_text.insert("end", "No tribe selected.")
            return

        score = self.world.tribal_relations.get(self.selected_tribe, 0)
        status = get_relation_status(score)
        queen = self.world.tribal_leaders.get(self.selected_tribe, "Unknown")
        description = self.get_relation_description(score)
        trait = self.world.tribal_traits.get(self.selected_tribe, "neutral") 

        profile = TRIBE_PROFILES.get(self.selected_tribe, {})
        blurb = profile.get("blurb", "No historical data available.")

        controlled_regions = self.get_regions_for_tribe(self.selected_tribe)

        hotspot_regions = sorted(
            [
                (region, self.world.region_activity.get(region, 0))
                for region in controlled_regions
            ],
            key=lambda x: x[1],
            reverse=True
        )

        if controlled_regions:
            controlled_regions_text = "\n".join(f"- {region}" for region in controlled_regions)
        else:
            controlled_regions_text = "None"

        active_hotspots = [item for item in hotspot_regions if item[1] > 0]

        if active_hotspots:
            hotspot_text = "\n".join(
                f"- {region} ({count})" for region, count in active_hotspots[:3]
            )
        else:
            hotspot_text = "None yet."

        tendencies = profile.get("tendencies", [])
        relations = profile.get("relations", {})

        profile_text = f"\nTribal Overview:\n{blurb}\n"

        if tendencies:
            profile_text += "\nTendencies:\n"
            for t in tendencies:
                profile_text += f"- {t}\n"

        if relations:
            profile_text += "\nHistorical Relations:\n"
            for tribe, desc in relations.items():
                profile_text += f"- {tribe}: {desc}\n"

        incidents = getattr(self.world, "tribal_incidents", {}).get(self.selected_tribe, [])

        if incidents:
            incident_text = "\n".join(f"- {i}" for i in incidents)
        else:
            incident_text = "None yet."

        detail_block = (
            f"Tribe: {self.selected_tribe}\n"
            f"Status: {status}\n"
            f"Queen: {queen}\n"
            f"Queen Traits: {trait}\n"
            f"Score: {score}\n\n"
            f"Description:\n{description}\n\n"
            f"Controlled Regions:\n{controlled_regions_text}\n\n"
            f"Regional Hotspots:\n{hotspot_text}\n\n"
            f"{profile_text}\n"
            f"Recent Incidents:\n{incident_text}\n"
        )
   
        self.detail_text.insert("end", detail_block)