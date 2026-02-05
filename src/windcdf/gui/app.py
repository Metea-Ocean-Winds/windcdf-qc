"""Main Tkinter application."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from windcdf.gui.state import AppState
from windcdf.gui.views.home_view import HomeView


class WindCDFApp:
    """Main application class for windcdf-qc GUI."""

    def __init__(self) -> None:
        """Initialize the application."""
        self.root = tk.Tk()
        self.root.title("windcdf-qc - Time Series QC Tool")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

        # Application state
        self.state = AppState()

        # Configure styles
        self._configure_styles()

        # Create main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Current view
        self.current_view: ttk.Frame | None = None

        # Show home view
        self.show_view("home")

    def _configure_styles(self) -> None:
        """Configure ttk styles."""
        style = ttk.Style()
        style.theme_use("clam")

    def show_view(self, view_name: str) -> None:
        """Switch to a different view.

        Args:
            view_name: Name of view to show.
        """
        # Clear current view
        if self.current_view is not None:
            self.current_view.destroy()

        # Create new view
        view_map = {
            "home": HomeView,
        }

        view_class = view_map.get(view_name)
        if view_class:
            self.current_view = view_class(self.main_frame, self)
            self.current_view.pack(fill=tk.BOTH, expand=True)

    def run(self) -> None:
        """Start the application main loop."""
        self.root.mainloop()

    def quit(self) -> None:
        """Quit the application."""
        self.root.quit()


def main() -> None:
    """Entry point for GUI."""
    app = WindCDFApp()
    app.run()


if __name__ == "__main__":
    main()
