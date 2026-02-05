"""Home view - welcome screen."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from windcdf.gui.app import WindCDFApp


class HomeView(ttk.Frame):
    """Home/welcome screen view."""

    def __init__(self, parent: ttk.Frame, app: WindCDFApp) -> None:
        """Initialize home view.

        Args:
            parent: Parent frame.
            app: Main application instance.
        """
        super().__init__(parent)
        self.app = app

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create view widgets."""
        # Title
        title_label = ttk.Label(
            self,
            text="windcdf-qc",
            font=("Helvetica", 24, "bold"),
        )
        title_label.pack(pady=30)

        # Subtitle
        subtitle_label = ttk.Label(
            self,
            text="Time Series Quality Control for Wind Measurements",
            font=("Helvetica", 12),
        )
        subtitle_label.pack(pady=10)

        # Buttons frame
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(pady=40)

        # Open file button
        open_btn = ttk.Button(
            buttons_frame,
            text="Open NetCDF File",
            command=self._on_open_file,
        )
        open_btn.pack(pady=10, ipadx=20, ipady=10)

        # Recent files (placeholder)
        recent_label = ttk.Label(
            self,
            text="Recent Files",
            font=("Helvetica", 10, "bold"),
        )
        recent_label.pack(pady=20)

        # Placeholder for recent files list
        recent_list = ttk.Label(
            self,
            text="No recent files",
            foreground="gray",
        )
        recent_list.pack()

    def _on_open_file(self) -> None:
        """Handle open file button click."""
        filepath = filedialog.askopenfilename(
            title="Select NetCDF File",
            filetypes=[
                ("NetCDF files", "*.nc"),
                ("All files", "*.*"),
            ],
        )
        if filepath:
            self._load_file(filepath)

    def _load_file(self, filepath: str) -> None:
        """Load a NetCDF file.

        Args:
            filepath: Path to NetCDF file.
        """
        try:
            from windcdf.io.reader import NetCDFReader

            reader = NetCDFReader(filepath)
            self.app.state.dataset = reader.open()
            self.app.state.filepath = filepath

            # Switch to time series view
            self.app.show_view("timeseries")
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to load file:\n{e}")
