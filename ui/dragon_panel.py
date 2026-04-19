import math
import random
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
from PIL import Image, ImageTk


class DragonPortraitPanel(ctk.CTkFrame):
    def __init__(self, parent, width=480, height=320):
        super().__init__(parent)

        self.width = width
        self.height = height
        self.dragon = None
        self.sprite_scale = 0.5

        self.use_sprite_tail = True   # set False to instantly go back
        self.tail_img = None
        self.tail_pivot = (12, 60)

        self.body_tail_socket = (275, 120)   # move red dot
        self.tail_root = (20, 130)           # move swing pivot within sprite

        self.tail_rotation_correction = (100, -62) # first number bigger equals right, second number bigger negative means up, move piece relative to red dot

        self.body_img = None
        self.body_pil = None



        try:
            base_dir = Path(__file__).resolve().parent
            tail_path = base_dir.parent / "assets" / "tail.png"
            print("TAIL PATH:", tail_path)

            tail_pil = Image.open(tail_path).convert("RGBA")
            tail_pil = tail_pil.resize(
                (
                    int(tail_pil.width * self.sprite_scale),
                    int(tail_pil.height * self.sprite_scale)
                ),
                Image.NEAREST
            )

            self.tail_pil = tail_pil
            self.tail_img = ImageTk.PhotoImage(self.tail_pil)
            self._tail_ref = self.tail_img

            print("TAIL SIZE:", self.tail_img.width(), self.tail_img.height())
        except Exception as e:
            print(f"Could not load tail sprite: {e}")
            self.tail_img = None
            self.use_sprite_tail = False



        
        try:
            body_path = base_dir.parent / "assets" / "body.png"

            body_pil = Image.open(body_path).convert("RGBA")
            body_pil = body_pil.resize(
                (
                    int(body_pil.width * self.sprite_scale),
                    int(body_pil.height * self.sprite_scale)
                ),
                Image.NEAREST
            )

            self.body_pil = body_pil
            self.body_img = ImageTk.PhotoImage(self.body_pil)
            self._body_ref = self.body_img

        except Exception as e:
            print(f"Could not load body sprite: {e}")
            self.body_img = None

        self.tick = 0
        self.blink_timer = random.randint(60, 180)
        self.blink_state = "open"

        self.canvas = tk.Canvas(
            self,
            width=self.width,
            height=self.height,
            bg="#1f1f1f",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        self.after(50, self.animate)


    def get_visual_state(self):
        d = self.dragon

        return {
            "body_type": d.body_type,
            "wing_type": d.wing_type,
            "leg_type": d.leg_type,
            "head_type": d.head_type,
            "snout_type": d.snout_type,
            "eye_style": d.eye_style,
            "tail_type": d.tail_type,
            "marking_type": d.marking_type,
            "scale_palette": d.scale_palette,
            "special_traits": d.special_visual_traits,
            "behavior": getattr(d, "behavior_type", "calm"),
            "personality": getattr(d, "personality", ""),
        }



    def get_body_color(self, tribe):
        palette_name = getattr(self.dragon, "scale_palette", "")

        palette_colors = {
            "mud_dark": "#5A4030",
            "mud_warm": "#7A5640",
            "mud_ash": "#6A625C",

            "night_black": "#1E1A24",
            "night_purple": "#332645",
            "night_blue": "#22304A",

            "sky_crimson": "#8B2E1E",
            "sky_orange": "#B3472A",
            "sky_rust": "#7A3A2A",

            "ice_pale": "#BFDDE8",
            "ice_blue": "#89C2D9",
            "ice_silver": "#C9D6DF",

            "sand_gold": "#B08A3E",
            "sand_tan": "#C2A56B",
            "sand_bronze": "#9A7440",

            "sea_teal": "#1F5D73",
            "sea_deep": "#18495A",
            "sea_blue": "#2D6F8A",

            "rain_green": "#3E8B4A",
            "rain_lime": "#5AAE5A",
            "rain_jade": "#2F7A63",

            "hive_gold": "#7A5C1B",
            "hive_olive": "#6E6A2C",
            "hive_amber": "#9B6B1F",

            "silk_lilac": "#8C5FA8",
            "silk_pink": "#B57AA8",
            "silk_blue": "#6D87B8",

            "leaf_moss": "#3F6B2F",
            "leaf_bright": "#5A8A42",
            "leaf_deep": "#2E5A24",

            "default": "#884444",
        }

        if palette_name:
            return palette_colors.get(palette_name, "#884444")

        fallback = {
            "MudWing": "#6B4F3A",
            "NightWing": "#2C2238",
            "SkyWing": "#8B2E1E",
            "IceWing": "#6FAFCF",
            "SandWing": "#B08A3E",
            "SeaWing": "#1F5D73",
            "RainWing": "#3E8B4A",
            "HiveWing": "#7A5C1B",
            "SilkWing": "#8C5FA8",
            "LeafWing": "#3F6B2F",
        }
        return fallback.get(tribe, "#884444")

    def get_eye_fill(self, eye_color):
        colors = {
            "amber": "#FFBF00",
            "green": "#66CC66",
            "blue": "#66A3FF",
            "violet": "#B266FF",
            "gold": "#FFD700",
            "brown": "#8B5A2B",
            "gray": "#B0B0B0",
        }
        return colors.get(eye_color.lower(), "gold") if eye_color else "gold"

    def draw_eyes(self, center_x, head_y, eye_fill):
        eye_style = getattr(self.dragon, "eye_style", "soft") or "soft"

        head_type = getattr(self.dragon, "head_type", "round")
        snout_type = getattr(self.dragon, "snout_type", "standard")

        # base positions
        eye_y = head_y + 5
        left_eye_x = center_x - 15
        right_eye_x = center_x + 15

        # head adjustments
        if head_type == "narrow":
            left_eye_x += 5
            right_eye_x -= 5

        elif head_type == "heavy":
            left_eye_x -= 5
            right_eye_x += 5
            eye_y += 2

        # snout adjustments
        if snout_type == "long":
            left_eye_x -= 2
            right_eye_x += 2

        elif snout_type == "short":
            left_eye_x += 2
            right_eye_x -= 2

        behavior = getattr(self.dragon, "behavior_type", "calm")

        if "aggressive" in behavior:
            eye_y -= 2  # eyes slightly higher = more intense

        elif "timid" in behavior:
            eye_y += 2  # softer, lower gaze

        offset = (self.dragon.id % 3) - 1  # -1, 0, or +1

        left_eye_x += offset
        right_eye_x -= offset

        if self.blink_state == "open":
            if eye_style == "soft":
                self.canvas.create_oval(
                    left_eye_x - 5, eye_y - 5,
                    left_eye_x + 5, eye_y + 5,
                    fill=eye_fill,
                    outline=""
                )
                self.canvas.create_oval(
                    right_eye_x - 5, eye_y - 5,
                    right_eye_x + 5, eye_y + 5,
                    fill=eye_fill,
                    outline=""
                )

            elif eye_style == "sharp":
                self.canvas.create_polygon(
                    left_eye_x - 6, eye_y,
                    left_eye_x + 2, eye_y - 4,
                    left_eye_x + 6, eye_y + 2,
                    left_eye_x - 2, eye_y + 4,
                    fill=eye_fill,
                    outline=""
                )
                self.canvas.create_polygon(
                    right_eye_x - 6, eye_y + 2,
                    right_eye_x + 2, eye_y - 4,
                    right_eye_x + 6, eye_y,
                    right_eye_x - 2, eye_y + 4,
                    fill=eye_fill,
                    outline=""
                )

            elif eye_style == "wide":
                self.canvas.create_oval(
                    left_eye_x - 7, eye_y - 6,
                    left_eye_x + 7, eye_y + 6,
                    fill=eye_fill,
                    outline=""
                )
                self.canvas.create_oval(
                    right_eye_x - 7, eye_y - 6,
                    right_eye_x + 7, eye_y + 6,
                    fill=eye_fill,
                    outline=""
                )

        else:
            self.canvas.create_line(
                left_eye_x - 6, eye_y,
                left_eye_x + 6, eye_y,
                fill=eye_fill,
                width=2
            )
            self.canvas.create_line(
                right_eye_x - 6, eye_y,
                right_eye_x + 6, eye_y,
                fill=eye_fill,
                width=2
            )




    def draw_head(self, center_x, head_y, body_color):
        tilt = ((self.dragon.id % 5) - 2)  # -2 to +2
        head_type = getattr(self.dragon, "head_type", "round") or "round"
        snout_type = getattr(self.dragon, "snout_type", "standard") or "standard"

        center_x = center_x + tilt
        head_y = head_y + 5

        if head_type == "round":
            self.canvas.create_oval(
                center_x - 35, head_y - 20,
                center_x + 35, head_y + 35,
                fill=body_color,
                outline=""
            )

        elif head_type == "angular":
            self.canvas.create_polygon(
                center_x - 35, head_y + 10,
                center_x - 10, head_y - 20,
                center_x + 25, head_y - 10,
                center_x + 35, head_y + 20,
                center_x, head_y + 35,
                fill=body_color,
                outline=""
            )

        elif head_type == "narrow":
            self.canvas.create_oval(
                center_x - 25, head_y - 20,
                center_x + 25, head_y + 35,
                fill=body_color,
                outline=""
            )

        elif head_type == "heavy":
            self.canvas.create_oval(
                center_x - 42, head_y - 18,
                center_x + 42, head_y + 38,
                fill=body_color,
                outline=""
            )

        # snout
        if snout_type == "short":
            self.canvas.create_polygon(
                center_x + 18, head_y + 5,
                center_x + 38, head_y + 12,
                center_x + 18, head_y + 20,
                fill=body_color,
                outline=""
            )

        elif snout_type == "standard":
            self.canvas.create_polygon(
                center_x + 20, head_y + 5,
                center_x + 48, head_y + 12,
                center_x + 20, head_y + 20,
                fill=body_color,
                outline=""
            )

        elif snout_type == "long":
            self.canvas.create_polygon(
                center_x + 20, head_y + 5,
                center_x + 62, head_y + 12,
                center_x + 20, head_y + 20,
                fill=body_color,
                outline=""
            )

        elif snout_type == "hooked":
            self.canvas.create_polygon(
                center_x + 20, head_y + 5,
                center_x + 55, head_y + 10,
                center_x + 48, head_y + 22,
                center_x + 20, head_y + 20,
                fill=body_color,
                outline=""
            )

    def draw_tail(self, left, top, breath_offset):
        behavior = getattr(self.dragon, "behavior_type", "calm")

        sway_speed = 10
        max_angle = 8

        if "aggressive" in behavior:
            sway_speed = 6
            max_angle = 12
        elif "calm" in behavior:
            sway_speed = 12
            max_angle = 8
        elif "timid" in behavior:
            sway_speed = 14
            max_angle = 5

        angle = math.sin(self.tick / sway_speed) * max_angle

        body_socket_x = left + self.body_tail_socket[0]
        body_socket_y = top + self.body_tail_socket[1]

        if self.use_sprite_tail and self.tail_img is not None:
            self.canvas.create_oval(
                body_socket_x - 3, body_socket_y - 3,
                body_socket_x + 3, body_socket_y + 3,
                fill="red",
                outline=""
            )

            rotated_tail = self.tail_pil.rotate(
                angle,
                resample=Image.NEAREST,
                center=self.tail_root,
                expand=True
            )

            rotated_tail_tk = ImageTk.PhotoImage(rotated_tail)
            self._tail_ref = rotated_tail_tk

            draw_x = body_socket_x + self.tail_rotation_correction[0]
            draw_y = body_socket_y + self.tail_rotation_correction[1]

            self.canvas.create_image(
                draw_x,
                draw_y,
                image=rotated_tail_tk,
                anchor="center"
            )
            return

        # --- ORIGINAL GEOMETRIC FALLBACK ---
        if tail_type == "standard":
            self.canvas.create_line(
                tail_base_x, tail_base_y,
                tail_base_x + 40, tail_base_y + 10 + sway,
                tail_base_x + 70, tail_base_y - 5,
                fill=body_color,
                width=8,
                smooth=True
            )

        elif tail_type == "long":
            self.canvas.create_line(
                tail_base_x, tail_base_y,
                tail_base_x + 60, tail_base_y + 20 + sway,
                tail_base_x + 100, tail_base_y - 10,
                fill=body_color,
                width=8,
                smooth=True
            )

        elif tail_type == "spiked":
            self.canvas.create_line(
                tail_base_x, tail_base_y,
                tail_base_x + 50, tail_base_y + 10 + sway,
                fill=body_color,
                width=8,
                smooth=True
            )
            self.canvas.create_polygon(
                tail_base_x + 50, tail_base_y + 10 + sway,
                tail_base_x + 65, tail_base_y - 5 + sway,
                tail_base_x + 70, tail_base_y + 15 + sway,
                fill="#CCCCCC",
                outline=""
            )

        elif tail_type == "thin":
            self.canvas.create_line(
                tail_base_x, tail_base_y,
                tail_base_x + 60, tail_base_y + sway,
                fill=body_color,
                width=4,
                smooth=True
            )

    def draw_horns(self, center_x, head_y, breath_offset):
        horn_type = getattr(self.dragon, "horn_type", "straight") or "straight"
        horn_color = "#AA9990"

        left_base_x = center_x - 20
        right_base_x = center_x + 20
        horn_base_y = head_y - 5

        if horn_type == "straight":
            self.canvas.create_polygon(
                left_base_x, horn_base_y,
                left_base_x - 18, horn_base_y - 35,
                left_base_x + 10, horn_base_y,
                fill=horn_color,
                outline=""
            )
            self.canvas.create_polygon(
                right_base_x, horn_base_y,
                right_base_x + 18, horn_base_y - 35,
                right_base_x - 10, horn_base_y,
                fill=horn_color,
                outline=""
            )

        elif horn_type == "wide":
            self.canvas.create_polygon(
                left_base_x, horn_base_y,
                left_base_x - 28, horn_base_y - 10,
                left_base_x + 8, horn_base_y - 2,
                fill=horn_color,
                outline=""
            )
            self.canvas.create_polygon(
                right_base_x, horn_base_y,
                right_base_x + 28, horn_base_y - 10,
                right_base_x - 8, horn_base_y - 2,
                fill=horn_color,
                outline=""
            )

        elif horn_type == "curved":
            self.canvas.create_line(
                left_base_x, horn_base_y,
                left_base_x - 12, horn_base_y - 15,
                left_base_x - 4, horn_base_y - 32,
                fill=horn_color,
                width=5,
                smooth=True
            )
            self.canvas.create_line(
                right_base_x, horn_base_y,
                right_base_x + 12, horn_base_y - 15,
                right_base_x + 4, horn_base_y - 32,
                fill=horn_color,
                width=5,
                smooth=True
            )

        elif horn_type == "stubby":
            self.canvas.create_polygon(
                left_base_x, horn_base_y,
                left_base_x - 8, horn_base_y - 14,
                left_base_x + 6, horn_base_y - 2,
                fill=horn_color,
                outline=""
            )
            self.canvas.create_polygon(
                right_base_x, horn_base_y,
                right_base_x + 8, horn_base_y - 14,
                right_base_x - 6, horn_base_y - 2,
                fill=horn_color,
                outline=""
            )

    def draw_body(self, left, right, top, bottom, body_color):
        body_type = getattr(self.dragon, "body_type", "lean") or "lean"

        if body_type == "lean":
            self.canvas.create_oval(
                left + 10, top,
                right - 10, bottom,
                fill=body_color,
                outline=""
            )

        elif body_type == "broad":
            self.canvas.create_oval(
                left - 10, top,
                right + 10, bottom,
                fill=body_color,
                outline=""
            )

        elif body_type == "tall":
            self.canvas.create_oval(
                left + 5, top - 10,
                right - 5, bottom + 10,
                fill=body_color,
                outline=""
            )

        elif body_type == "compact":
            self.canvas.create_oval(
                left + 15, top + 10,
                right - 15, bottom - 10,
                fill=body_color,
                outline=""
            )


    def draw_markings(self, left, right, top, bottom):
        marking = getattr(self.dragon, "marking_type", "none") or "none"

        # slightly lighter/darker overlay color
        overlay_color = "#222222"

        if marking == "stripes":
            for i in range(3):
                y = top + 20 + i * 20
                self.canvas.create_line(
                    left + 20, y,
                    right - 20, y,
                    fill=overlay_color,
                    width=2
                )

        elif marking == "spots":
            for i in range(4):
                x = left + 30 + i * 25
                y = top + 30 + (i % 2) * 20
                self.canvas.create_oval(
                    x - 5, y - 5,
                    x + 5, y + 5,
                    fill=overlay_color,
                    outline=""
                )

        elif marking == "belly":
            self.canvas.create_oval(
                left + 15, top + 25,
                right - 15, bottom - 5,
                fill="#d9c2a3",
                outline=""
            )


    def draw_special_traits(self, left, right, top, bottom):
        traits = getattr(self.dragon, "special_visual_traits", [])

        if not traits:
            return

        for trait in traits:

            if trait == "bright_bioluminescence":
                self.canvas.create_oval(
                    left + 10, top + 10,
                    right - 10, bottom - 10,
                    outline="#66FFFF",
                    width=2
                )

            elif trait == "silver_sheen":
                self.canvas.create_oval(
                    left, top,
                    right, bottom,
                    outline="#DDDDDD",
                    width=2
                )

            elif trait == "black_diamond_pattern":
                self.canvas.create_polygon(
                    (left + right) // 2, top + 10,
                    left + 30, top + 40,
                    (left + right) // 2, top + 70,
                    right - 30, top + 40,
                    fill="#111111",
                    outline=""
                )

            elif trait == "strong_star_pattern":
                star_points = [
                    (left + 40, top + 20),
                    (right - 50, top + 30),
                    (left + 60, bottom - 35),
                    (right - 70, bottom - 25),
                    ((left + right) // 2, top + 50),
                ]
                for x, y in star_points:
                    self.canvas.create_oval(x, y, x + 3, y + 3, fill="white", outline="")

            elif trait == "leaf_vein_pattern":
                center_x = (left + right) // 2
                self.canvas.create_line(
                    center_x, top + 10,
                    center_x, bottom - 10,
                    fill="#224422",
                    width=2
                )
                self.canvas.create_line(
                    center_x, top + 30,
                    center_x - 20, top + 50,
                    fill="#224422",
                    width=1
                )
                self.canvas.create_line(
                    center_x, top + 45,
                    center_x + 22, top + 65,
                    fill="#224422",
                    width=1
                )

            elif trait == "vivid_scales":
                self.canvas.create_oval(
                    left + 5, top + 5,
                    right - 5, bottom - 5,
                    outline="#00FF88",
                    width=2
                )

            elif trait == "amber_underscales":
                self.canvas.create_oval(
                    left + 18, top + 35,
                    right - 18, bottom - 8,
                    fill="#D89B2B",
                    outline=""
                )

            elif trait == "bright_scales":
                self.canvas.create_oval(
                    left + 3, top + 3,
                    right - 3, bottom - 3,
                    outline="#FFD166",
                    width=3
                )

            elif trait == "pale_scales":
                self.canvas.create_oval(
                    left + 6, top + 6,
                    right - 6, bottom - 6,
                    outline="#F2E8D5",
                    width=2
                )

            elif trait == "heavy_black_marking":
                self.canvas.create_oval(
                    left + 20, top + 20,
                    right - 20, bottom - 20,
                    fill="#1A1A1A",
                    outline=""
                )

            elif trait == "vivid_wings":
                # placeholder wing accents until real wings exist
                self.canvas.create_polygon(
                    left + 10, top + 40,
                    left - 30, top + 70,
                    left + 5, bottom - 10,
                    fill="#C86BFF",
                    outline=""
                )
                self.canvas.create_polygon(
                    right - 10, top + 40,
                    right + 30, top + 70,
                    right - 5, bottom - 10,
                    fill="#C86BFF",
                    outline=""
                )

    def draw_wings(self, center_x, wing_mid_y, left, right, top, bottom):
        wing_type = getattr(self.dragon, "wing_type", "standard") or "standard"

        body_color = self.get_body_color(self.dragon.tribe)

        # make some special traits affect wings
        traits = getattr(self.dragon, "special_visual_traits", [])
        wing_color = body_color
        wing_outline = ""

        # base position
        wing_base_left = center_x - 25
        wing_base_right = center_x + 25
        mid_y = wing_mid_y

        if "vivid_wings" in traits:
            wing_color = "#C86BFF"
        elif "silver_sheen" in traits:
            wing_outline = "#DDDDDD"

        mid_y = wing_mid_y

        if wing_type == "standard":
            left_points = [
                wing_base_left, mid_y,
                left - 40, top + 20,
                left - 20, bottom - 10,
            ]
            right_points = [
                wing_base_right, mid_y,
                right + 40, top + 20,
                right + 20, bottom - 10,
            ]

        elif wing_type == "large":
            left_points = [
                wing_base_left, mid_y,
                left - 65, top + 10,
                left - 35, bottom,
            ]
            right_points = [
                wing_base_right, mid_y,
                right + 65, top + 10,
                right + 35, bottom,
            ]

        elif wing_type == "sleek":
            left_points = [
                wing_base_left, mid_y,
                left - 55, mid_y - 10,
                left - 10, bottom - 5,
            ]
            right_points = [
                wing_base_right, mid_y,
                right + 55, mid_y - 10,
                right + 10, bottom - 5,
            ]

        elif wing_type == "tattered":
            left_points = [
                wing_base_left, mid_y,
                left - 50, top + 20,
                left - 25, bottom - 15,
            ]
            right_points = [
                wing_base_right, mid_y,
                right + 50, top + 20,
                right + 25, bottom - 15,
            ]
        else:
            left_points = [
                wing_base_left, mid_y,
                left - 40, top + 20,
                left - 20, bottom - 10,
            ]
            right_points = [
                wing_base_right, mid_y,
                right + 40, top + 20,
                right + 20, bottom - 10,
            ]

        self.canvas.create_polygon(*left_points, fill=wing_color, outline=wing_outline)
        self.canvas.create_polygon(*right_points, fill=wing_color, outline=wing_outline)

        if wing_type == "tattered":
            self.canvas.create_line(
                left - 18, bottom - 5,
                left - 5, bottom - 20,
                fill="#1f1f1f",
                width=2
            )
            self.canvas.create_line(
                right + 18, bottom - 5,
                right + 5, bottom - 20,
                fill="#1f1f1f",
                width=2
            )


    def draw_legs(self, center_x, leg_base_y):
        leg_type = getattr(self.dragon, "leg_type", "standard") or "standard"
        body_color = self.get_body_color(self.dragon.tribe)

        # behavior affects stance
        behavior = getattr(self.dragon, "behavior_type", "calm")

        stance_offset = 0
        if "aggressive" in behavior:
            stance_offset = 5
        elif "timid" in behavior:
            stance_offset = -3

        # base positions
        front_x = center_x - 15 + stance_offset
        back_x = center_x + 15 + stance_offset
        y_top = leg_base_y - 8

        if leg_type == "standard":
            length = 20
            width = 6

        elif leg_type == "thick":
            length = 20
            width = 10

        elif leg_type == "long":
            length = 30
            width = 6

        elif leg_type == "short":
            length = 12
            width = 6

        else:
            length = 20
            width = 6

        # front leg
        self.canvas.create_line(
            front_x, y_top,
            front_x, y_top + length,
            fill=body_color,
            width=width
        )

        # back leg
        self.canvas.create_line(
            back_x, y_top,
            back_x, y_top + length,
            fill=body_color,
            width=width
        )



    def set_dragon(self, dragon):
        self.dragon = dragon
        self.tick = 0
        self.blink_timer = random.randint(60, 180)
        self.blink_state = "open"
        self.redraw()

    def animate(self):
        self.tick += 1
        self.blink_timer -= 1

        if self.blink_timer <= 0:
            if self.blink_state == "open":
                self.blink_state = "closed"
                self.blink_timer = 6
            else:
                self.blink_state = "open"
                self.blink_timer = random.randint(80, 220)

        self.redraw()
        self.after(50, self.animate)

    def redraw(self):
        self.canvas.delete("all")

        if not self.dragon:
            self.canvas.create_text(
                self.width // 2,
                self.height // 2,
                text="No dragon selected",
                fill="white",
                font=("Arial", 16)
            )
            return

        state = self.get_visual_state()

        # breathing animation / behavior based
        behavior = state["behavior"]

        speed = 8
        amplitude = 2

        if "aggressive" in behavior:
            speed = 5
            amplitude = 3
        elif "calm" in behavior:
            speed = 10
            amplitude = 2
        elif "timid" in behavior:
            speed = 12
            amplitude = 1

        breath_offset = int(math.sin(self.tick / speed) * amplitude)

        # body color
        body_color = self.get_body_color(self.dragon.tribe)

        # eye color
        eye_fill = self.get_eye_fill(getattr(self.dragon, "eye_color", ""))

        # Height influences body size a little
        dragon_height = getattr(self.dragon, "height", 5.5)
        size_scale = max(0.85, min(1.2, dragon_height / 5.5))

        body_width = int(140 * size_scale)
        body_height = int(100 * size_scale)

        left = (self.width // 2) - (body_width // 2)
        right = (self.width // 2) + (body_width // 2)
        top = 80 + breath_offset
        bottom = top + body_height

        center_x = (left + right) // 2

        body_mid_y = (top + bottom) // 2
        head_y = top + 25 + breath_offset
        leg_base_y = bottom + (breath_offset // 2)
        wing_mid_y = top + 40 + breath_offset

        if "timid" in behavior:
            top += 5
        elif "aggressive" in behavior:
            left -= 5
            right -= 5



        # wings 2nd in order
        self.draw_wings(center_x, wing_mid_y, left, right, top, bottom)

        # body 3rd in oder
        if self.body_img:
            self.canvas.create_image(
                left,
                top,
                image=self.body_img,
                anchor="nw"
            )

        # legs 4th in order
        self.draw_legs(center_x, leg_base_y)

        # markings 5th in order
        self.draw_markings(left, right, top, bottom)

        # special traits 6th in order
        self.draw_special_traits(left, right, top, bottom)

        # head 7th in order
        self.draw_head(center_x, head_y, body_color)

        # horns 8th in order
        self.draw_horns(center_x, head_y, breath_offset)

        # eyes 9th in order
        self.draw_eyes(center_x, head_y, eye_fill)

        # tail 1st in order
        self.draw_tail(left, top, breath_offset)

        # simple scar indicator if dragon has scars
        scars = getattr(self.dragon, "scars", [])
        if scars:
            self.canvas.create_line(
                left + 35, top + 25,
                left + 50, top + 45,
                fill="#DDDDDD",
                width=2
            )

        # dead dragons look dimmer
        if getattr(self.dragon, "status", "Alive") == "Dead":
            self.canvas.create_rectangle(
                0, 0, self.width, self.height,
                fill="#000000",
                stipple="gray50",
                outline=""
            )

        # label
        self.canvas.create_text(
            self.width // 2,
            210,
            text=f"{self.dragon.name} ({self.dragon.tribe})",
            fill="white",
            font=("Arial", 14, "bold")
        )