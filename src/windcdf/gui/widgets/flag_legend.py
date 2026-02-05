"""Flag legend widget."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from windcdf.models.flags import FlagSeverity


# Colors for flag severity levels
FLAG_COLORS = {
    FlagSeverity.GOOD: "#2ecc71",      # Green
    FlagSeverity.SUSPECT: "#f39c12",   # Orange
    FlagSeverity.BAD: "#e74c3c",       # Red
    FlagSeverity.MISSING: "#95a5a6",   # Gray
}


class FlagLegend(ttk.Frame):
    """Widget showing flag color legend."""

    def __init__(self, parent: tk.Widget) -> None:
        """Initialize flag legend.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        ttk.Label(self, text="Flag Legend", font=("Helvetica", 10, "bold")).pack(pady=5)

        for severity in FlagSeverity:
            item_frame = ttk.Frame(self)
            item_frame.pack(fill=tk.X, padx=5, pady=2)

            # Color indicator
            color_canvas = tk.Canvas(item_frame, width=16, height=16)
            color_canvas.pack(side=tk.LEFT, padx=5)
            color_canvas.create_rectangle(
                2, 2, 14, 14,
                fill=FLAG_COLORS[severity],
                outline="",
            )

            # Label
            ttk.Label(item_frame, text=severity.name.capitalize()).pack(side=tk.LEFT)
