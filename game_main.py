import sys
from ui.app import DragonGenApp


def run_game(starting_tribe="mixed"):
    app = DragonGenApp(starting_tribe=starting_tribe)
    app.mainloop()


if __name__ == "__main__":
    starting_tribe = sys.argv[1] if len(sys.argv) > 1 else "mixed"
    run_game(starting_tribe)