"""File open view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from windcdf.gui.app import WindCDFApp


class FileOpenView(ttk.Frame):
    """File browser and selection view."""

    def __init__(self, parent: ttk.Frame, app: WindCDFApp) -> None:
        """Initialize file open view.

        Args:
            parent: Parent frame.
            app: Main application instance.
        """
        super().__init__(parent)
        self.app = app

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create view widgets."""
        # Header
        header = ttk.Label(self, text="Open NetCDF File", font=("Helvetica", 16))
        header.pack(pady=20)

        # File selection frame
        file_frame = ttk.Frame(self)
        file_frame.pack(fill=tk.X, padx=20, pady=10)

        self.filepath_var = tk.StringVar()
        filepath_entry = ttk.Entry(
            file_frame,
            textvariable=self.filepath_var,
            width=60,
        )
        filepath_entry.pack(side=tk.LEFT, padx=5)

        browse_btn = ttk.Button(
            file_frame,
            text="Browse",
            command=self._browse_file,
        )
        browse_btn.pack(side=tk.LEFT, padx=5)

        # Open button
        open_btn = ttk.Button(
            self,
            text="Open",
            command=self._open_file,
        )
        open_btn.pack(pady=20)

    def _browse_file(self) -> None:
        """Open file browser dialog."""
        filepath = filedialog.askopenfilename(
            title="Select NetCDF File",
            filetypes=[
                ("NetCDF files", "*.nc"),
                ("All files", "*.*"),
            ],
        )
        if filepath:
            self.filepath_var.set(filepath)

    def _open_file(self) -> None:
        """Load the selected file."""
        filepath = self.filepath_var.get()
        if not filepath:
            return

        try:
            from windcdf.io.reader import NetCDFReader

            reader = NetCDFReader(filepath)
            self.app.state.dataset = reader.open()
            self.app.state.filepath = filepath
            self.app.show_view("timeseries")
        except Exception as e:
            tk.messagebox.showerror("Error", f"Failed to load file:\n{e}")
