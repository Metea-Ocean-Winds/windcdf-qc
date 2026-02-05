"""Time series view with plots and flag overlays."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from windcdf.gui.app import WindCDFApp


class TimeSeriesView(ttk.Frame):
    """Main time series visualization view."""

    def __init__(self, parent: ttk.Frame, app: WindCDFApp) -> None:
        """Initialize time series view.

        Args:
            parent: Parent frame.
            app: Main application instance.
        """
        super().__init__(parent)
        self.app = app

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create view widgets."""
        # Create paned window for resizable layout
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left panel - variable list
        left_frame = ttk.Frame(paned, width=200)
        paned.add(left_frame, weight=1)

        var_label = ttk.Label(left_frame, text="Variables", font=("Helvetica", 12, "bold"))
        var_label.pack(pady=10)

        self.var_listbox = tk.Listbox(left_frame, selectmode=tk.MULTIPLE)
        self.var_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.var_listbox.bind("<<ListboxSelect>>", self._on_variable_select)

        # Populate variables
        self._populate_variables()

        # Right panel - plot area
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=4)

        # Toolbar
        toolbar = ttk.Frame(right_frame)
        toolbar.pack(fill=tk.X)

        run_qc_btn = ttk.Button(toolbar, text="Run QC", command=self._run_qc)
        run_qc_btn.pack(side=tk.LEFT, padx=5, pady=5)

        export_btn = ttk.Button(toolbar, text="Export", command=self._export)
        export_btn.pack(side=tk.LEFT, padx=5, pady=5)

        # Plot canvas placeholder
        self.plot_frame = ttk.Frame(right_frame, relief=tk.SUNKEN)
        self.plot_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        plot_label = ttk.Label(
            self.plot_frame,
            text="Select variables to plot",
            foreground="gray",
        )
        plot_label.pack(expand=True)

    def _populate_variables(self) -> None:
        """Populate variable listbox from dataset."""
        if self.app.state.dataset is None:
            return

        self.var_listbox.delete(0, tk.END)
        for var in self.app.state.dataset.data_vars:
            self.var_listbox.insert(tk.END, var)

    def _on_variable_select(self, event) -> None:
        """Handle variable selection change."""
        selection = self.var_listbox.curselection()
        self.app.state.selected_variables = [
            self.var_listbox.get(i) for i in selection
        ]
        self._update_plot()

    def _update_plot(self) -> None:
        """Update the plot with selected variables."""
        # Placeholder - matplotlib integration would go here
        pass

    def _run_qc(self) -> None:
        """Run QC checks on selected variables."""
        if not self.app.state.selected_variables:
            tk.messagebox.showwarning("Warning", "Please select variables first")
            return

        try:
            from windcdf.qc.engine import QCEngine

            engine = QCEngine()
            self.app.state.qc_report = engine.run(
                self.app.state.dataset,
                variables=self.app.state.selected_variables,
            )
            self._update_plot()
            tk.messagebox.showinfo(
                "QC Complete",
                f"Found {self.app.state.qc_report.total_flags} flags",
            )
        except Exception as e:
            tk.messagebox.showerror("Error", f"QC failed:\n{e}")

    def _export(self) -> None:
        """Export QC results."""
        # Placeholder for export functionality
        tk.messagebox.showinfo("Export", "Export functionality coming soon")
