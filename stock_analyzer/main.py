from __future__ import annotations

import tkinter as tk

from .gui import StockAnalyzerApp


def run() -> None:
    root = tk.Tk()
    app = StockAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    run()
