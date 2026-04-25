import math
import random
import tkinter as tk
import customtkinter as ctk
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw

#ROTATION_ENABLED = FALSE (off) TRUE (on)

class DragonPortraitPanel(ctk.CTkFrame):
    def __init__(self, parent, width=320, height=440):
        super().__init__(parent)

        base_dir = Path(__file__).resolve().parent

        self.width = width
        self.height = height
        self.dragon = None
        self.sprite_scale = 0.5

#TAIL
        self.use_sprite_tail = True   # set False to instantly go back
        self.tail_img = None

        self.body_tail_socket = (268, 110)   # move red dot
        self.tail_root = (26, 154)        # move swing pivot within sprite

        self.tail_rotation_correction = (0, 0) # first number bigger equals right, second number bigger negative means up, move piece relative to red dot

#BODY
        self.body_img = None
        self.body_pil = None

#NECK
        self.use_sprite_neck = True
        self.neck_img = None
        self.neck_pil = None

#HEAD
        self.use_sprite_head = True
        self.head_img = None
        self.head_pil = None

        self.head_open_pil = None
        self.head_half_pil = None
        self.head_closed_pil = None

        self.blink_state = "open"
        self.blink_phase = "idle"
        self.blink_timer = random.randint(80, 220)

        self.body_neck_socket = (39, 12)   # on body image
        self.neck_root = (24, 110)           # on neck image, where it meets body
        self.neck_head_socket = (27, 30)    # on neck image, where head attaches
        self.head_root = (42, 51)           # on head image, where it meets neck

        self.head_rotation_correction = (0, 0)

#LEFT WING (BACK)
        self.use_sprite_wing_left = True
        self.wing_left_img = None
        self.wing_left_pil = None

        self.body_left_wing_socket = (70, 50)   # starting guess on body
        self.wing_left_root = (15, 166)         # starting guess inside wing sprite

#RIGHT WING (FRONT)
        self.use_sprite_wing_right = True
        self.wing_right_img = None
        self.wing_right_pil = None

        self.body_right_wing_socket = (80, 60)   # starting guess on body
        self.wing_right_root = (15, 166)         # starting guess inside wing sprite


# FEET
        self.use_sprite_feet = True
        self.feet_img = None
        self.feet_pil = None

        self.body_feet_socket = (98, 103)   # starting guess
        self.feet_root = (60, 20)            # starting guess inside feet sprite

        self.feet_rotation_enabled = False
        self.feet_rotation_correction = (0, 0)



        try:
            head_open_path = base_dir.parent / "assets" / "head_open.png"
            head_half_path = base_dir.parent / "assets" / "head_half.png"
            head_closed_path = base_dir.parent / "assets" / "head_closed.png"

            self.head_open_pil = Image.open(head_open_path).convert("RGBA")
            self.head_half_pil = Image.open(head_half_path).convert("RGBA")
            self.head_closed_pil = Image.open(head_closed_path).convert("RGBA")

            self.head_open_pil = self.head_open_pil.resize(
                (
                    int(self.head_open_pil.width * self.sprite_scale),
                    int(self.head_open_pil.height * self.sprite_scale)
                ),
                Image.NEAREST
            )

            self.head_half_pil = self.head_half_pil.resize(
                (
                    int(self.head_half_pil.width * self.sprite_scale),
                    int(self.head_half_pil.height * self.sprite_scale)
                ),
                Image.NEAREST
            )

            self.head_closed_pil = self.head_closed_pil.resize(
                (
                    int(self.head_closed_pil.width * self.sprite_scale),
                    int(self.head_closed_pil.height * self.sprite_scale)
                ),
                Image.NEAREST
            )

        except Exception as e:
            print(f"Could not load head blink frames: {e}")


        try:
            neck_path = base_dir.parent / "assets" / "neck.png"

            neck_pil = Image.open(neck_path).convert("RGBA")
            neck_pil = neck_pil.resize(
                (
                    int(neck_pil.width * self.sprite_scale),
                    int(neck_pil.height * self.sprite_scale)
                ),
                Image.NEAREST
            )

            self.neck_pil = neck_pil
            self.neck_img = ImageTk.PhotoImage(self.neck_pil)
            self._neck_ref = self.neck_img

        except Exception as e:
            print(f"Could not load neck sprite: {e}")
            self.neck_img = None
            self.use_sprite_neck = False


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


        try:
            wing_left_path = base_dir.parent / "assets" / "wing_left.png"

            wing_left_pil = Image.open(wing_left_path).convert("RGBA")
            wing_left_pil = wing_left_pil.resize(
                (
                    int(wing_left_pil.width * self.sprite_scale),
                    int(wing_left_pil.height * self.sprite_scale)
                ),
                Image.NEAREST
            )

            self.wing_left_pil = wing_left_pil
            self.wing_left_img = ImageTk.PhotoImage(self.wing_left_pil)
            self._wing_left_ref = self.wing_left_img

        except Exception as e:
            print(f"Could not load left wing sprite: {e}")
            self.wing_left_img = None
            self.use_sprite_wing_left = False


        try:
            wing_right_path = base_dir.parent / "assets" / "wing_right.png"

            wing_right_pil = Image.open(wing_right_path).convert("RGBA")
            wing_right_pil = wing_right_pil.resize(
                (
                    int(wing_right_pil.width * self.sprite_scale),
                    int(wing_right_pil.height * self.sprite_scale)
                ),
                Image.NEAREST
            )

            self.wing_right_pil = wing_right_pil
            self.wing_right_img = ImageTk.PhotoImage(self.wing_right_pil)
            self._wing_right_ref = self.wing_right_img

        except Exception as e:
            print(f"Could not load right wing sprite: {e}")
            self.wing_right_img = None
            self.use_sprite_wing_right = False


        try:
            feet_path = base_dir.parent / "assets" / "feet.png"

            feet_pil = Image.open(feet_path).convert("RGBA")
            feet_pil = feet_pil.resize(
                (
                    int(feet_pil.width * self.sprite_scale),
                    int(feet_pil.height * self.sprite_scale)
                ),
                Image.NEAREST
            )

            self.feet_pil = feet_pil
            self.feet_img = ImageTk.PhotoImage(self.feet_pil)
            self._feet_ref = self.feet_img

        except Exception as e:
            print(f"Could not load feet sprite: {e}")
            self.feet_img = None
            self.use_sprite_feet = False


    def clamp_rgb(self, value):
        return max(0, min(255, int(value)))

    def vary_color(self, rgb, shift_r=0, shift_g=0, shift_b=0, brightness=1.0):
        r, g, b = rgb
        r = self.clamp_rgb((r + shift_r) * brightness)
        g = self.clamp_rgb((g + shift_g) * brightness)
        b = self.clamp_rgb((b + shift_b) * brightness)
        return (r, g, b)

    def recolor_grayscale_image(self, image, dark_rgb, mid_rgb, light_rgb):
        img = image.convert("RGBA")
        pixels = img.load()
        w, h = img.size
    
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
    
                if a == 0:
                    continue

                brightness = (r + g + b) / 3 / 255.0

                # optional: preserve very bright belly/white highlights more
                if brightness > 0.92:
                    continue

                if brightness < 0.5:
                    t = brightness / 0.5
                    nr = int(dark_rgb[0] * (1 - t) + mid_rgb[0] * t)
                    ng = int(dark_rgb[1] * (1 - t) + mid_rgb[1] * t)
                    nb = int(dark_rgb[2] * (1 - t) + mid_rgb[2] * t)
                else:
                    t = (brightness - 0.5) / 0.5
                    nr = int(mid_rgb[0] * (1 - t) + light_rgb[0] * t)
                    ng = int(mid_rgb[1] * (1 - t) + light_rgb[1] * t)
                    nb = int(mid_rgb[2] * (1 - t) + light_rgb[2] * t)
    
                pixels[x, y] = (nr, ng, nb, a)
    
        return img

    def get_individualized_ramp(self, tribe):
        dark_rgb, mid_rgb, light_rgb = self.get_tribe_color_ramp(tribe)

        dragon_id = getattr(self.dragon, "id", 0)

        hue_shift = (dragon_id % 5) - 2
        green_shift = ((dragon_id // 3) % 5) - 2
        bright_shift = ((dragon_id // 7) % 5) - 2

        shift_r = hue_shift * 6
        shift_g = green_shift * 6
        shift_b = -hue_shift * 4
        brightness = 1.0 + (bright_shift * 0.04)

        varied_dark = self.vary_color(dark_rgb, shift_r, shift_g, shift_b, brightness)
        varied_mid = self.vary_color(mid_rgb, shift_r, shift_g, shift_b, brightness)
        varied_light = self.vary_color(light_rgb, shift_r, shift_g, shift_b, brightness)

        return varied_dark, varied_mid, varied_light

    def get_recolored_part(self, pil_image):
        if pil_image is None or self.dragon is None:
            return pil_image

        dark_rgb, mid_rgb, light_rgb = self.get_individualized_ramp(self.dragon.tribe)
        return self.recolor_grayscale_image(pil_image, dark_rgb, mid_rgb, light_rgb)


    def recolor_grayscale_image(self, image, dark_rgb, mid_rgb, light_rgb):
        """
        Recolor a grayscale RGBA sprite using a 3-color ramp while preserving alpha.
        Assumes the image is grayscale or close to grayscale.
        """
        img = image.convert("RGBA")
        pixels = img.load()
        w, h = img.size

        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
        
                if a == 0:
                    continue

                # brightness from 0 to 1
                brightness = (r + g + b) / 3 / 255.0

                if brightness < 0.5:
                    # blend dark -> mid
                    t = brightness / 0.5
                    nr = int(dark_rgb[0] * (1 - t) + mid_rgb[0] * t)
                    ng = int(dark_rgb[1] * (1 - t) + mid_rgb[1] * t)
                    nb = int(dark_rgb[2] * (1 - t) + mid_rgb[2] * t)
                else:
                    # blend mid -> light
                    t = (brightness - 0.5) / 0.5
                    nr = int(mid_rgb[0] * (1 - t) + light_rgb[0] * t)
                    ng = int(mid_rgb[1] * (1 - t) + light_rgb[1] * t)
                    nb = int(mid_rgb[2] * (1 - t) + light_rgb[2] * t)

                pixels[x, y] = (nr, ng, nb, a)
        
        return img

    def clamp_rgb(self, value):
        return max(0, min(255, int(value)))


    def vary_color(self, rgb, shift_r=0, shift_g=0, shift_b=0, brightness=1.0):
        r, g, b = rgb
        r = self.clamp_rgb((r + shift_r) * brightness)
        g = self.clamp_rgb((g + shift_g) * brightness)
        b = self.clamp_rgb((b + shift_b) * brightness)
        return (r, g, b)


    def get_individualized_ramp(self, tribe):
        dark_rgb, mid_rgb, light_rgb = self.get_tribe_color_ramp(tribe)

        dragon_id = getattr(self.dragon, "id", 0)

        # stable per-dragon offsets
        hue_shift = (dragon_id % 5) - 2          # -2 to +2
        green_shift = ((dragon_id // 3) % 5) - 2 # -2 to +2
        bright_shift = ((dragon_id // 7) % 5) - 2

        # subtle values only
        shift_r = hue_shift * 6
        shift_g = green_shift * 6
        shift_b = -hue_shift * 4

        brightness = 1.0 + (bright_shift * 0.04)

        varied_dark = self.vary_color(dark_rgb, shift_r, shift_g, shift_b, brightness)
        varied_mid = self.vary_color(mid_rgb, shift_r, shift_g, shift_b, brightness)
        varied_light = self.vary_color(light_rgb, shift_r, shift_g, shift_b, brightness)

        return varied_dark, varied_mid, varied_light


    def get_tribe_color_ramp(self, tribe):
        ramps = {
            "MudWing": ((60, 40, 28), (110, 79, 58), (160, 125, 95)),
            "NightWing": ((20, 18, 28), (45, 40, 65), (90, 85, 120)),
            "SkyWing": ((90, 25, 18), (150, 55, 35), (220, 120, 70)),
            "IceWing": ((120, 160, 180), (170, 210, 230), (230, 245, 255)),
            "SandWing": ((120, 90, 40), (180, 145, 80), (235, 210, 150)),
            "SeaWing": ((10, 40, 55), (40, 130, 170), (140, 220, 240)), 
            "RainWing": ((30, 90, 45), (60, 160, 80), (140, 230, 120)),
            "HiveWing": ((90, 70, 25), (150, 120, 40), (220, 180, 80)),
            "SilkWing": ((80, 60, 110), (140, 110, 180), (220, 190, 240)),
            "LeafWing": ((30, 80, 35), (60, 130, 60), (130, 200, 110)),
        }
        return ramps.get(tribe, ((50, 50, 50), (130, 130, 130), (220, 220, 220)))


    def draw_feet_sprite(self, left, top):
        if not self.use_sprite_feet or self.feet_img is None:
            return

        feet_socket_x = left + self.body_feet_socket[0]
        feet_socket_y = top + self.body_feet_socket[1]

        self.canvas.create_oval(
            feet_socket_x - 3, feet_socket_y - 3,
            feet_socket_x + 3, feet_socket_y + 3,
            fill="dodgerblue",
            outline=""
        )

        angle = 0
        if self.feet_rotation_enabled:
            angle = math.sin(self.tick / 12) * 4

        recolored_feet = self.get_recolored_part(self.feet_pil)

        pivot_canvas = self.make_pivot_canvas(
            recolored_feet,
            self.feet_root,
            debug_color="orange"
        )

        rotated_feet = pivot_canvas.rotate(
            angle,
            resample=Image.NEAREST,
            expand=False
        )
    
        rotated_feet_tk = ImageTk.PhotoImage(rotated_feet)
        self._feet_ref = rotated_feet_tk

        draw_x = feet_socket_x + self.feet_rotation_correction[0]
        draw_y = feet_socket_y + self.feet_rotation_correction[1]

        self.canvas.create_image(
            draw_x,
            draw_y,
            image=rotated_feet_tk,
            anchor="center"
        )


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

    def make_pivot_canvas(self, image, pivot_xy, debug_color=None):
        """
        Create a larger transparent square canvas and paste the sprite into it
        so that pivot_xy inside the sprite lands exactly at the center.
        """
        w, h = image.size
        px, py = pivot_xy

        # Make a big enough square so rotation won't clip
        side = int(math.ceil(max(w, h) * 2.5))
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))

        cx = side // 2
        cy = side // 2

        # Paste sprite so chosen pivot lands in the center
        paste_x = int(cx - px)
        paste_y = int(cy - py)

        canvas.paste(image, (paste_x, paste_y), image)

        # Optional debug dot at the true pivot
        if debug_color:
            draw = ImageDraw.Draw(canvas)
            r = 4
            draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=debug_color)

        return canvas



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


    def draw_sprite_part(
        self,
        pil_image,
        socket_x,
        socket_y,
        root,
        angle=0,
        debug_color=None,
        recolor_mode="body",
        dim_factor=None,
        ref_attr="_part_ref"
    ):
        """
        Generic sprite-part renderer.

        pil_image: PIL image for the part
        socket_x/socket_y: where the part attaches on canvas
        root: pivot/root point inside the sprite
        angle: rotation angle in degrees
        debug_color: optional pivot debug dot color
        recolor_mode: "body", "wing", or None
        dim_factor: optional brightness multiplier after rotation
        ref_attr: attribute name to store PhotoImage reference
        """
        if pil_image is None:
            return

        # recolor
        if recolor_mode == "body":
            part_img = self.get_recolored_part(pil_image)
        elif recolor_mode == "wing":
            part_img = self.get_recolored_wing_part(pil_image)
        else:
            part_img = pil_image

        pivot_canvas = self.make_pivot_canvas(
            part_img,
            root,
            debug_color=debug_color
        )

        rotated = pivot_canvas.rotate(
            angle,
            resample=Image.NEAREST,
            expand=False
        )

        if dim_factor is not None:
            rotated = rotated.copy().point(lambda p: int(p * dim_factor))

        tk_img = ImageTk.PhotoImage(rotated)
        setattr(self, ref_attr, tk_img)

        self.canvas.create_image(
            socket_x,
            socket_y,
            image=tk_img,
            anchor="center"
        )


    def rotate_point(self, x, y, angle_deg):
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
    
        rx = x * cos_a - y * sin_a
        ry = x * sin_a + y * cos_a
        return rx, ry



    def rotate_image_about_pivot(self, image, angle_deg, pivot_xy):
        """
        Rotate a PIL image around pivot_xy and return:
        - rotated PIL image
        - new pivot position inside rotated image
        """
        px, py = pivot_xy
        w, h = image.size

        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Original image corners relative to pivot
        corners = [
            (-px,     -py),
            (w - px,  -py),
            (w - px,  h - py),
            (-px,     h - py),
        ]

        # Rotate corners
        rotated = []
        for x, y in corners:
            rx = x * cos_a - y * sin_a
            ry = x * sin_a + y * cos_a
            rotated.append((rx, ry))

        min_x = min(x for x, y in rotated)
        min_y = min(y for x, y in rotated)
        max_x = max(x for x, y in rotated)
        max_y = max(y for x, y in rotated)

        new_w = int(math.ceil(max_x - min_x))
        new_h = int(math.ceil(max_y - min_y))

        # Where pivot ends up inside the expanded rotated image
        new_pivot_x = -min_x
        new_pivot_y = -min_y

        rotated_img = image.rotate(
            angle_deg,
            resample=Image.NEAREST,
            center=pivot_xy,
            expand=True
        )

        return rotated_img, (new_pivot_x, new_pivot_y)


    def draw_left_wing(self, left, top):
        if not self.use_sprite_wing_left or self.wing_left_img is None:
            return

        behavior = getattr(self.dragon, "behavior_type", "calm")

        flap_speed = 12
        max_angle = 10

        if "aggressive" in behavior:
            flap_speed = 8
            max_angle = 16
        elif "timid" in behavior:
            flap_speed = 16
            max_angle = 6

        angle = math.sin((self.tick - 3)/ flap_speed) * max_angle

        wing_socket_x = left + self.body_left_wing_socket[0]
        wing_socket_y = top + self.body_left_wing_socket[1]

        self.canvas.create_oval(
            wing_socket_x - 3, wing_socket_y - 3,
            wing_socket_x + 3, wing_socket_y + 3,
            fill="magenta",
            outline=""
        )

        recolored_left_wing = self.get_recolored_wing_part(self.wing_left_pil)
        
        pivot_canvas = self.make_pivot_canvas(
            recolored_left_wing,
            self.wing_left_root,
            debug_color="white"
        )

        rotated_wing = pivot_canvas.rotate(
            angle,
            resample=Image.NEAREST,
            expand=False
        )

        rotated_wing = rotated_wing.copy()
        rotated_wing = rotated_wing.point(lambda p: int(p * 0.85))  # slight dim

        rotated_wing_tk = ImageTk.PhotoImage(rotated_wing)
        self._wing_left_ref = rotated_wing_tk

        self.canvas.create_image(
            wing_socket_x,
            wing_socket_y,
            image=rotated_wing_tk,
            anchor="center"
        )


    def draw_right_wing(self, left, top):
        if not self.use_sprite_wing_right or self.wing_right_img is None:
            return

        behavior = getattr(self.dragon, "behavior_type", "calm")

        flap_speed = 12
        max_angle = 10

        if "aggressive" in behavior:
            flap_speed = 8
            max_angle = 16
        elif "timid" in behavior:
            flap_speed = 16
            max_angle = 6

        angle = math.sin(self.tick / flap_speed) * max_angle

        wing_socket_x = left + self.body_right_wing_socket[0]
        wing_socket_y = top + self.body_right_wing_socket[1]

        self.canvas.create_oval(
            wing_socket_x - 3, wing_socket_y - 3,
            wing_socket_x + 3, wing_socket_y + 3,
            fill="magenta",
            outline=""
        )

        recolored_right_wing = self.get_recolored_wing_part(self.wing_right_pil)

        pivot_canvas = self.make_pivot_canvas(
            recolored_right_wing,
            self.wing_right_root,
            debug_color="white"
        )

        rotated_wing = pivot_canvas.rotate(
            angle,
            resample=Image.NEAREST,
            expand=False
        )

        rotated_wing_tk = ImageTk.PhotoImage(rotated_wing)
        self._wing_right_ref = rotated_wing_tk

        self.canvas.create_image(
            wing_socket_x,
            wing_socket_y,
            image=rotated_wing_tk,
            anchor="center"
        )

    
    def draw_head_sprite(self, neck_socket_x, neck_socket_y, neck_angle):
        if not self.use_sprite_head or self.head_open_pil is None:
            return
    
        if self.blink_state == "open":
            current_head = self.head_open_pil
        elif self.blink_state == "half":
            current_head = self.head_half_pil
        else:
            current_head = self.head_closed_pil
    
        behavior = getattr(self.dragon, "behavior_type", "calm")
    
        sway_speed = 14
        max_angle = 4
    
        if "aggressive" in behavior:
            sway_speed = 10
            max_angle = 6
        elif "timid" in behavior:
            sway_speed = 18
            max_angle = 3
    
        head_local_angle = math.sin(self.tick / sway_speed) * max_angle
    
        # vector from neck root to head socket, in neck-image space
        offset_x = self.neck_head_socket[0] - self.neck_root[0]
        offset_y = self.neck_head_socket[1] - self.neck_root[1]
    
        rotated_offset_x, rotated_offset_y = self.rotate_point(offset_x, offset_y, neck_angle)

        final_head_socket_x = neck_socket_x + rotated_offset_x
        final_head_socket_y = neck_socket_y + rotated_offset_y
    
        final_head_angle = neck_angle + head_local_angle
    
        self.canvas.create_oval(
            final_head_socket_x - 3, final_head_socket_y - 3,
            final_head_socket_x + 3, final_head_socket_y + 3,
            fill="orange",
            outline=""
        )
    
        self.draw_sprite_part(
            pil_image=current_head,
            socket_x=final_head_socket_x,
            socket_y=final_head_socket_y,
            root=self.head_root,
            angle=final_head_angle,
            debug_color="orange",
            recolor_mode="body",
            ref_attr="_head_ref"
        )
        

    def rotate_point(self, x, y, angle_deg):
        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
    
        rx = x * cos_a - y * sin_a
        ry = x * sin_a + y * cos_a
        return rx, ry


    def draw_neck(self, left, top):
        if not self.use_sprite_neck or self.neck_pil is None:
            return None
    
        body_socket_x = left + self.body_neck_socket[0]
        body_socket_y = top + self.body_neck_socket[1]
    
        behavior = getattr(self.dragon, "behavior_type", "calm")
    
        sway_speed = 16
        max_angle = 3
    
        if "aggressive" in behavior:
            sway_speed = 12
            max_angle = 5
        elif "timid" in behavior:
            sway_speed = 20
            max_angle = 2

        neck_angle = math.sin(self.tick / sway_speed) * max_angle

        self.canvas.create_oval(
            body_socket_x - 3, body_socket_y - 3,
            body_socket_x + 3, body_socket_y + 3,
            fill="cyan",
            outline=""
        )

        self.draw_sprite_part(
            pil_image=self.neck_pil,
            socket_x=body_socket_x,
            socket_y=body_socket_y,
            root=self.neck_root,
            angle=neck_angle,
            debug_color="cyan",
            recolor_mode="body",
            ref_attr="_neck_ref"
        )

        return body_socket_x, body_socket_y, neck_angle


    def get_recolored_wing_part(self, pil_image):
        if pil_image is None or self.dragon is None:
            return pil_image
    
        dark_rgb, mid_rgb, light_rgb = self.get_individualized_ramp(self.dragon.tribe)
    
        # wings usually look better a little lighter/airier than body scales
        wing_dark = self.vary_color(dark_rgb, 0, 0, 0, 1.03)
        wing_mid = self.vary_color(mid_rgb, 0, 0, 0, 1.06)
        wing_light = self.vary_color(light_rgb, 0, 0, 0, 1.08)
    
        return self.recolor_grayscale_image(pil_image, wing_dark, wing_mid, wing_light)


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
    
            self.draw_sprite_part(
                pil_image=self.tail_pil,
                socket_x=body_socket_x,
                socket_y=body_socket_y,
                root=self.tail_root,
                angle=angle,
                debug_color="lime",
                recolor_mode="body",
                ref_attr="_tail_ref"
            )
            return


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

            if self.blink_phase == "idle":
                # start blink
                self.blink_state = "half"
                self.blink_phase = "closing"
                self.blink_timer = 3

            elif self.blink_phase == "closing":
                if self.blink_state == "half":
                    self.blink_state = "closed"
                    self.blink_timer = 3
                elif self.blink_state == "closed":
                    self.blink_state = "half"
                    self.blink_phase = "opening"
                    self.blink_timer = 3

            elif self.blink_phase == "opening":
                if self.blink_state == "half":
                    self.blink_state = "open"
                    self.blink_phase = "idle"
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

        if self.body_img:
            body_width = self.body_img.width()
            body_height = self.body_img.height()
        else:
            body_width = int(140 * size_scale)
            body_height = int(100 * size_scale)

        left = (self.width // 2) - (body_width // 2) + 230
        top = 220 + breath_offset
        right = left + body_width
        bottom = top + body_height

        wing_influence = math.sin(self.tick / 10) * 2
        top += wing_influence
        bottom += wing_influence

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
        #self.draw_wings(center_x, wing_mid_y, left, right, top, bottom)
        self.draw_left_wing(left, top)

        # tail 1st in order
        self.draw_tail(left, top, breath_offset)

        # body 3rd in oder
        if self.body_pil:
            recolored_body = self.get_recolored_part(self.body_pil)
            recolored_body_tk = ImageTk.PhotoImage(recolored_body)
            self._body_ref = recolored_body_tk

            self.canvas.create_image(
                left,
                top,
                image=recolored_body_tk,
                anchor="nw"
            )

        # legs 4th in order
        #self.draw_legs(center_x, leg_base_y)
        self.draw_feet_sprite(left, top)

        # markings 5th in order
        #off for now, self.draw_markings(left, right, top, bottom)

        # special traits 6th in order
        #off for nowself.draw_special_traits(left, right, top, bottom)

        # neck/head 7th in order
        neck_data = self.draw_neck(left, top)

        if neck_data is not None:
            neck_socket_x, neck_socket_y, neck_angle = neck_data
            self.draw_head_sprite(neck_socket_x, neck_socket_y, neck_angle)
        else:
             self.draw_head(center_x, head_y, body_color)

        # wings 2nd in order
        #self.draw_wings(center_x, wing_mid_y, left, right, top, bottom)
        self.draw_right_wing(left, top)

        # horns 8th in order
        # off for now, self.draw_horns(center_x, head_y, breath_offset)

        # eyes 9th in order
        # off for now, self.draw_eyes(center_x, head_y, eye_fill)

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