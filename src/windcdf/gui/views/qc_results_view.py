"""QC results view."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from windcdf.gui.app import WindCDFApp


class QCResultsView(ttk.Frame):
    """View for reviewing and managing QC results."""

    def __init__(self, parent: ttk.Frame, app: WindCDFApp) -> None:
        """Initialize QC results view.

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
        header = ttk.Label(self, text="QC Results", font=("Helvetica", 16))
        header.pack(pady=10)

        # Summary frame
        summary_frame = ttk.LabelFrame(self, text="Summary")
        summary_frame.pack(fill=tk.X, padx=10, pady=5)

        self.summary_label = ttk.Label(summary_frame, text="No results available")
        self.summary_label.pack(padx=10, pady=10)

        # Results tree
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("timestamp", "variable", "severity", "check", "message")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")

        self.tree.heading("timestamp", text="Timestamp")
        self.tree.heading("variable", text="Variable")
        self.tree.heading("severity", text="Severity")
        self.tree.heading("check", text="Check")
        self.tree.heading("message", text="Message")

        self.tree.column("timestamp", width=150)
        self.tree.column("variable", width=100)
        self.tree.column("severity", width=80)
        self.tree.column("check", width=100)
        self.tree.column("message", width=300)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Update with current results
        self._update_results()

    def _update_results(self) -> None:
        """Update results display."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        report = self.app.state.qc_report
        if report is None:
            self.summary_label.config(text="No results available")
            return

        # Update summary
        summary_text = f"Total flags: {report.total_flags}\n"
        for severity, count in report.flags_by_severity.items():
            summary_text += f"  {severity}: {count}\n"
        self.summary_label.config(text=summary_text)

        # Populate tree
        for flag in report.flags:
            self.tree.insert("", tk.END, values=(
                flag.timestamp.isoformat() if flag.timestamp else "N/A",
                flag.variable,
                flag.severity.name,
                flag.check_name,
                flag.message,
            ))
