"""Settings view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from windcdf.gui.app import WindCDFApp


class SettingsView(ttk.Frame):
    """Application settings view."""

    def __init__(self, parent: ttk.Frame, app: WindCDFApp) -> None:
        """Initialize settings view.

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
        header = ttk.Label(self, text="Settings", font=("Helvetica", 16))
        header.pack(pady=10)

        # QC Settings
        qc_frame = ttk.LabelFrame(self, text="QC Settings")
        qc_frame.pack(fill=tk.X, padx=10, pady=5)

        # Spike check settings
        spike_frame = ttk.Frame(qc_frame)
        spike_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(spike_frame, text="Spike threshold:").pack(side=tk.LEFT)
        self.spike_threshold = ttk.Entry(spike_frame, width=10)
        self.spike_threshold.insert(0, "3.0")
        self.spike_threshold.pack(side=tk.LEFT, padx=5)

        # Stuck sensor settings
        stuck_frame = ttk.Frame(qc_frame)
        stuck_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(stuck_frame, text="Min stuck count:").pack(side=tk.LEFT)
        self.stuck_count = ttk.Entry(stuck_frame, width=10)
        self.stuck_count.insert(0, "6")
        self.stuck_count.pack(side=tk.LEFT, padx=5)

        # Display Settings
        display_frame = ttk.LabelFrame(self, text="Display")
        display_frame.pack(fill=tk.X, padx=10, pady=5)

        self.show_good_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            display_frame,
            text="Show GOOD flags",
            variable=self.show_good_var,
        ).pack(anchor=tk.W, padx=5)

        self.show_suspect_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            display_frame,
            text="Show SUSPECT flags",
            variable=self.show_suspect_var,
        ).pack(anchor=tk.W, padx=5)

        self.show_bad_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            display_frame,
            text="Show BAD flags",
            variable=self.show_bad_var,
        ).pack(anchor=tk.W, padx=5)

        # Apply button
        apply_btn = ttk.Button(self, text="Apply", command=self._apply_settings)
        apply_btn.pack(pady=20)

    def _apply_settings(self) -> None:
        """Apply current settings."""
        self.app.state.show_good = self.show_good_var.get()
        self.app.state.show_suspect = self.show_suspect_var.get()
        self.app.state.show_bad = self.show_bad_var.get()

        tk.messagebox.showinfo("Settings", "Settings applied")
