import sys
from ui.app import DragonGenApp

if __name__ == "__main__":
    starting_tribe = sys.argv[1] if len(sys.argv) > 1 else "mixed"

    app = DragonGenApp(starting_tribe=starting_tribe)
    app.mainloop()