"""Toolbar widget."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable


class Toolbar(ttk.Frame):
    """Application toolbar widget."""

    def __init__(self, parent: tk.Widget) -> None:
        """Initialize toolbar.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._buttons: dict[str, ttk.Button] = {}

    def add_button(
        self,
        name: str,
        text: str,
        command: Callable[[], None],
        **kwargs,
    ) -> ttk.Button:
        """Add a button to the toolbar.

        Args:
            name: Button identifier.
            text: Button text.
            command: Button callback.
            **kwargs: Additional button options.

        Returns:
            Created button widget.
        """
        btn = ttk.Button(self, text=text, command=command, **kwargs)
        btn.pack(side=tk.LEFT, padx=2, pady=2)
        self._buttons[name] = btn
        return btn

    def add_separator(self) -> None:
        """Add a separator to the toolbar."""
        sep = ttk.Separator(self, orient=tk.VERTICAL)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)

    def enable_button(self, name: str) -> None:
        """Enable a button by name."""
        if name in self._buttons:
            self._buttons[name].state(["!disabled"])

    def disable_button(self, name: str) -> None:
        """Disable a button by name."""
        if name in self._buttons:
            self._buttons[name].state(["disabled"])
