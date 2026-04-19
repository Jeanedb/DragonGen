import customtkinter as ctk
from core.sim.conversations import build_conversation, apply_conversation_choice


class ConversationPanel(ctk.CTkToplevel):
    def __init__(self, parent, world):
        super().__init__(parent)
        self.world = world

        self.title("Conversation")
        self.geometry("700x500")

        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

        self.selected_a = None
        self.selected_b = None
        self.current_convo = None

        self.dragons = [d for d in world.dragons if d.status == "Alive"]

        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.pack(fill="x", padx=10, pady=10)

        dragon_names = [f"{d.name} ({d.id})" for d in self.dragons]

        self.a_menu = ctk.CTkOptionMenu(self.top_frame, values=dragon_names)
        self.a_menu.pack(side="left", padx=5)

        self.b_menu = ctk.CTkOptionMenu(self.top_frame, values=dragon_names)
        self.b_menu.pack(side="left", padx=5)

        self.start_btn = ctk.CTkButton(
            self.top_frame,
            text="Start Conversation",
            command=self.start_conversation
        )
        self.start_btn.pack(side="left", padx=5)

        self.text_box = ctk.CTkTextbox(self, wrap="word")
        self.text_box.pack(fill="both", expand=True, padx=10, pady=10)

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(fill="x", padx=10, pady=(0, 10))

    def get_dragon_from_menu(self, menu_value):
        dragon_id = int(menu_value.split("(")[-1].replace(")", ""))
        return next((d for d in self.dragons if d.id == dragon_id), None)

    def clear_option_buttons(self):
        for widget in self.button_frame.winfo_children():
            widget.destroy()

    def start_conversation(self):
        self.clear_option_buttons()
        self.text_box.delete("1.0", "end")

        a = self.get_dragon_from_menu(self.a_menu.get())
        b = self.get_dragon_from_menu(self.b_menu.get())

        if not a or not b:
            self.text_box.insert("end", "Could not find both dragons.")
            return

        if a.id == b.id:
            self.text_box.insert("end", "Choose two different dragons.")
            return

        convo = build_conversation(self.world, a, b)

        self.selected_a = a
        self.selected_b = b
        self.current_convo = convo

        self.text_box.insert("end", convo["text"])

        for option in convo["options"]:
            btn = ctk.CTkButton(
                self.button_frame,
                text=option["text"],
                command=lambda oid=option["id"]: self.resolve_conversation(oid)
            )
            btn.pack(side="left", padx=5, pady=5)

    def resolve_conversation(self, option_id):
        self.clear_option_buttons()

        if not self.current_convo or not self.selected_a or not self.selected_b:
            return

        player_line, reply_line, result_text = apply_conversation_choice(
            self.world,
            self.selected_a,
            self.selected_b,
            self.current_convo["type"],
            option_id
        )

        self.text_box.insert("end", f"\n\n{player_line}")
        self.text_box.insert("end", f"\n\n{reply_line}")
        self.text_box.insert("end", f"\n\n{result_text}")