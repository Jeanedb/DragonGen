from PIL import Image, ImageTk
import tkinter as tk

root = tk.Tk()
root.geometry("800x600")

img = Image.open("C:/DragonGen/assets/tail.png").convert("RGBA")
tk_img = ImageTk.PhotoImage(img)

print("Loaded:", tk_img.width(), tk_img.height())

canvas = tk.Canvas(root, width=800, height=600, bg="white")
canvas.pack(fill="both", expand=True)

canvas.create_image(100, 100, image=tk_img, anchor="nw")

root.mainloop()