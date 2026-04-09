import customtkinter as ctk
from core.sim.politics import get_relation_status


class TribalRelationsWindow(ctk.CTkToplevel):
    def __init__(self, parent, world):
        super().__init__(parent)

        self.world = world
        self.selected_tribe = None
        self.tribe_buttons = []

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

            btn = ctk.CTkButton(
                self.tribe_scroll,
                text=f"{tribe} — {status} ({score})",
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
        description = self.get_relation_description(score)

        detail_block = (
            f"Tribe: {self.selected_tribe}\n"
            f"Status: {status}\n"
            f"Score: {score}\n\n"
            f"Description:\n{description}\n\n"
            f"Recent Incidents:\n"
            f"None yet.\n"
        )

        self.detail_text.insert("end", detail_block)