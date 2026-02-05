"""Status bar widget."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class StatusBar(ttk.Frame):
    """Application status bar widget."""

    def __init__(self, parent: tk.Widget) -> None:
        """Initialize status bar.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)

        self._message_var = tk.StringVar(value="Ready")
        self._progress_var = tk.DoubleVar(value=0)

        # Message label
        self._message_label = ttk.Label(
            self,
            textvariable=self._message_var,
            anchor=tk.W,
        )
        self._message_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Progress bar (hidden by default)
        self._progress_bar = ttk.Progressbar(
            self,
            variable=self._progress_var,
            length=100,
            mode="determinate",
        )

    def set_message(self, message: str) -> None:
        """Set status bar message.

        Args:
            message: Message to display.
        """
        self._message_var.set(message)

    def show_progress(self, value: float = 0) -> None:
        """Show progress bar.

        Args:
            value: Initial progress value (0-100).
        """
        self._progress_var.set(value)
        self._progress_bar.pack(side=tk.RIGHT, padx=5)

    def update_progress(self, value: float) -> None:
        """Update progress bar value.

        Args:
            value: Progress value (0-100).
        """
        self._progress_var.set(value)

    def hide_progress(self) -> None:
        """Hide progress bar."""
        self._progress_bar.pack_forget()

    def set_busy(self, message: str = "Working...") -> None:
        """Set busy state with indeterminate progress.

        Args:
            message: Status message.
        """
        self.set_message(message)
        self._progress_bar.config(mode="indeterminate")
        self._progress_bar.pack(side=tk.RIGHT, padx=5)
        self._progress_bar.start()

    def clear_busy(self, message: str = "Ready") -> None:
        """Clear busy state.

        Args:
            message: Status message after clearing.
        """
        self._progress_bar.stop()
        self._progress_bar.config(mode="determinate")
        self._progress_bar.pack_forget()
        self.set_message(message)
