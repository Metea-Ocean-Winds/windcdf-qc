"""Main Tkinter application for the WindCDF Interactive QC Tool."""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, ttk
from typing import Any

import numpy as np

from windcdf.qc_tool.data_model import (
    QC_FLAGS,
    DatasetManager,
    SeriesIdentifier,
)
from windcdf.qc_tool.plotting import QCPlotCanvas


class SelectionTreeview(ttk.Frame):
    """Hierarchical selection table for datasets, variables, and series."""
    
    def __init__(self, master, on_selection_change: callable,
                 on_color_change: callable | None = None):
        super().__init__(master)
        self.on_selection_change = on_selection_change
        self.on_color_change = on_color_change
        
        # Treeview with columns for color, QC checkbox and plot assignments
        columns = ("color", "qc", "p1", "p2", "p3", "p4")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings", 
                                  selectmode="extended")
        
        # Configure columns
        self.tree.heading("#0", text="Item")
        self.tree.heading("color", text="Color")
        self.tree.heading("qc", text="QC")
        self.tree.heading("p1", text="P1")
        self.tree.heading("p2", text="P2")
        self.tree.heading("p3", text="P3")
        self.tree.heading("p4", text="P4")
        
        self.tree.column("#0", width=200, stretch=True)
        self.tree.column("color", width=50, anchor="center")
        self.tree.column("qc", width=40, anchor="center")
        self.tree.column("p1", width=40, anchor="center")
        self.tree.column("p2", width=40, anchor="center")
        self.tree.column("p3", width=40, anchor="center")
        self.tree.column("p4", width=40, anchor="center")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Layout
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind click events
        self.tree.bind("<Button-1>", self._on_click)
        
        # Store item data
        self.item_data: dict[str, Any] = {}
        
        # Track states
        self.qc_enabled: dict[str, bool] = {}
        self.plot_assignments: dict[str, int | None] = {}  # series_id -> plot index
        self.series_colors: dict[str, str] = {}  # item -> color hex
    
    def clear(self) -> None:
        """Clear all items."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.item_data.clear()
        self.qc_enabled.clear()
        self.plot_assignments.clear()
        self.series_colors.clear()
    
    def _generate_random_color(self) -> str:
        """Generate a random hex color."""
        import random
        r = random.randint(50, 200)
        g = random.randint(50, 200)
        b = random.randint(50, 200)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def add_dataset(self, dataset_id: str, variables: list[str], 
                    get_series_func: callable) -> None:
        """Add a dataset with its variables and series to the tree."""
        # Add dataset node
        ds_node = self.tree.insert("", "end", text=dataset_id, open=True)
        
        for var_name in variables:
            # Add variable node
            var_node = self.tree.insert(ds_node, "end", text=var_name, open=True)
            
            # Get series for this variable
            series_list = get_series_func(dataset_id, var_name)
            
            for series_id in series_list:
                # Create display name for series
                if series_id.series_key:
                    series_text = ", ".join(f"{k}={v}" for k, v in series_id.series_key)
                else:
                    series_text = "(single series)"
                
                # Generate random color for series
                color = self._generate_random_color()
                
                # Add series node with color box
                series_node = self.tree.insert(
                    var_node, "end", text=series_text,
                    values=("■", "☐", "○", "○", "○", "○")
                )
                
                # Store mapping
                self.item_data[series_node] = series_id
                self.qc_enabled[series_node] = False
                self.plot_assignments[series_node] = None
                self.series_colors[series_node] = color
                
                # Apply color tag
                self._update_item_display(series_node)
    
    def _on_click(self, event) -> None:
        """Handle click on tree item."""
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        
        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        
        if not item or item not in self.item_data:
            return
        
        col_index = int(column[1:]) - 1  # Convert #1 to 0, etc.
        
        if col_index == 0:  # Color column
            self._pick_color(item)
        elif col_index == 1:  # QC column
            self._toggle_qc(item)
        elif col_index >= 2 and col_index <= 5:  # P1-P4 columns
            self._toggle_plot(item, col_index - 2)
    
    def _pick_color(self, item: str) -> None:
        """Open color picker for an item."""
        current_color = self.series_colors.get(item, "#808080")
        result = colorchooser.askcolor(color=current_color, title="Choose Series Color")
        if result[1]:  # result is ((r, g, b), hex_color) or (None, None)
            self.series_colors[item] = result[1]
            self._update_item_display(item)
            if self.on_color_change:
                series_id = self.item_data[item]
                self.on_color_change(series_id, result[1])
    
    def _toggle_qc(self, item: str) -> None:
        """Toggle QC enabled state for an item."""
        self.qc_enabled[item] = not self.qc_enabled[item]
        self._update_item_display(item)
        self.on_selection_change()
    
    def _toggle_plot(self, item: str, plot_index: int) -> None:
        """Toggle plot assignment for an item."""
        current = self.plot_assignments[item]
        
        if current == plot_index:
            # Deselect
            self.plot_assignments[item] = None
        else:
            # Select this plot
            self.plot_assignments[item] = plot_index
        
        self._update_item_display(item)
        self.on_selection_change()
    
    def _update_item_display(self, item: str) -> None:
        """Update the display values for an item."""
        # Get color (use square symbol - actual color shown via tag)
        color = self.series_colors.get(item, "#808080")
        color_char = "■"
        
        qc_char = "☑" if self.qc_enabled.get(item, False) else "☐"
        
        plot_chars = []
        current_plot = self.plot_assignments.get(item)
        for i in range(4):
            if current_plot == i:
                plot_chars.append("●")
            else:
                plot_chars.append("○")
        
        self.tree.item(item, values=(color_char, qc_char, *plot_chars))
        
        # Create and apply color tag
        tag_name = f"color_{item}"
        self.tree.tag_configure(tag_name, foreground=color)
        self.tree.item(item, tags=(tag_name,))
    
    def get_series_colors(self) -> dict[SeriesIdentifier, str]:
        """Get color mapping for all series."""
        colors = {}
        for item, series_id in self.item_data.items():
            if item in self.series_colors:
                colors[series_id] = self.series_colors[item]
        return colors
    
    def get_qc_enabled_series(self) -> list[SeriesIdentifier]:
        """Get list of series with QC enabled."""
        enabled = []
        for item, is_enabled in self.qc_enabled.items():
            if is_enabled and item in self.item_data:
                enabled.append(self.item_data[item])
        return enabled
    
    def get_plot_assignments(self) -> dict[int, list[SeriesIdentifier]]:
        """Get series assignments for each plot."""
        assignments: dict[int, list[SeriesIdentifier]] = {i: [] for i in range(4)}
        
        for item, plot_idx in self.plot_assignments.items():
            if plot_idx is not None and item in self.item_data:
                assignments[plot_idx].append(self.item_data[item])
        
        return assignments


class TimeSliderControl(ttk.Frame):
    """Time range slider with pan controls."""
    
    def __init__(self, master, on_range_change: callable):
        super().__init__(master)
        self.on_range_change = on_range_change
        
        self.time_min: np.datetime64 | None = None
        self.time_max: np.datetime64 | None = None
        self.view_start: float = 0.0  # 0-1 normalized
        self.view_end: float = 1.0
        
        # Pan left button
        self.pan_left_btn = ttk.Button(self, text="<", width=3, 
                                       command=self._pan_left)
        self.pan_left_btn.pack(side="left", padx=2)
        
        # Time slider frame (using two scales)
        slider_frame = ttk.Frame(self)
        slider_frame.pack(side="left", fill="x", expand=True, padx=5)
        
        ttk.Label(slider_frame, text="Start:").pack(side="left")
        self.start_scale = ttk.Scale(slider_frame, from_=0, to=100, 
                                     orient="horizontal", command=self._on_start_change)
        self.start_scale.pack(side="left", fill="x", expand=True, padx=2)
        
        ttk.Label(slider_frame, text="End:").pack(side="left")
        self.end_scale = ttk.Scale(slider_frame, from_=0, to=100,
                                   orient="horizontal", command=self._on_end_change)
        self.end_scale.set(100)
        self.end_scale.pack(side="left", fill="x", expand=True, padx=2)
        
        # Pan right button
        self.pan_right_btn = ttk.Button(self, text=">", width=3,
                                        command=self._pan_right)
        self.pan_right_btn.pack(side="left", padx=2)
    
    def set_time_bounds(self, time_min: np.datetime64, time_max: np.datetime64) -> None:
        """Set the full time range."""
        self.time_min = time_min
        self.time_max = time_max
        self.view_start = 0.0
        self.view_end = 1.0
        self.start_scale.set(0)
        self.end_scale.set(100)
    
    def _on_start_change(self, value) -> None:
        """Handle start slider change."""
        self.view_start = float(value) / 100.0
        if self.view_start >= self.view_end:
            self.view_start = self.view_end - 0.01
            self.start_scale.set(self.view_start * 100)
        self._notify_change()
    
    def _on_end_change(self, value) -> None:
        """Handle end slider change."""
        self.view_end = float(value) / 100.0
        if self.view_end <= self.view_start:
            self.view_end = self.view_start + 0.01
            self.end_scale.set(self.view_end * 100)
        self._notify_change()
    
    def _pan_left(self) -> None:
        """Pan left by current window fraction."""
        pan_amount = (self.view_end - self.view_start) * 0.25
        if self.view_start - pan_amount >= 0:
            self.view_start -= pan_amount
            self.view_end -= pan_amount
        else:
            diff = self.view_end - self.view_start
            self.view_start = 0.0
            self.view_end = diff
        
        self.start_scale.set(self.view_start * 100)
        self.end_scale.set(self.view_end * 100)
        self._notify_change()
    
    def _pan_right(self) -> None:
        """Pan right by current window fraction."""
        pan_amount = (self.view_end - self.view_start) * 0.25
        if self.view_end + pan_amount <= 1.0:
            self.view_start += pan_amount
            self.view_end += pan_amount
        else:
            diff = self.view_end - self.view_start
            self.view_end = 1.0
            self.view_start = 1.0 - diff
        
        self.start_scale.set(self.view_start * 100)
        self.end_scale.set(self.view_end * 100)
        self._notify_change()
    
    def _notify_change(self) -> None:
        """Notify callback of range change."""
        if self.time_min is None or self.time_max is None:
            return
        
        delta = self.time_max - self.time_min
        total_range = delta.astype("timedelta64[us]").astype(float)
        start_offset = int(total_range * self.view_start)
        end_offset = int(total_range * self.view_end)
        
        view_min = self.time_min + np.timedelta64(start_offset, "us")
        view_max = self.time_min + np.timedelta64(end_offset, "us")
        
        self.on_range_change(view_min, view_max)
    
    def set_zoom(self, zoom_percent: float) -> None:
        """Set zoom level (100 = full range, 50 = zoom 2x)."""
        zoom_fraction = zoom_percent / 100.0
        
        # Zoom centered on current view
        current_center = (self.view_start + self.view_end) / 2.0
        half_width = zoom_fraction / 2.0
        
        new_start = current_center - half_width
        new_end = current_center + half_width
        
        # Clamp to bounds
        if new_start < 0:
            new_end -= new_start
            new_start = 0
        if new_end > 1:
            new_start -= (new_end - 1)
            new_end = 1
        
        new_start = max(0, new_start)
        new_end = min(1, new_end)
        
        self.view_start = new_start
        self.view_end = new_end
        self.start_scale.set(self.view_start * 100)
        self.end_scale.set(self.view_end * 100)
        self._notify_change()


class ZoomSliderControl(ttk.Frame):
    """Zoom slider control."""
    
    def __init__(self, master, on_zoom_change: callable):
        super().__init__(master)
        self.on_zoom_change = on_zoom_change
        
        ttk.Label(self, text="Zoom:").pack(side="left", padx=5)
        
        self.zoom_scale = ttk.Scale(self, from_=10, to=100, orient="horizontal",
                                    command=self._on_zoom_change)
        self.zoom_scale.set(100)
        self.zoom_scale.pack(side="left", fill="x", expand=True, padx=5)
        
        self.zoom_label = ttk.Label(self, text="100%", width=6)
        self.zoom_label.pack(side="left", padx=5)
    
    def _on_zoom_change(self, value) -> None:
        """Handle zoom slider change."""
        zoom_val = float(value)
        self.zoom_label.config(text=f"{int(zoom_val)}%")
        self.on_zoom_change(zoom_val)


class QCToolApp:
    """Main application class for the WindCDF Interactive QC Tool."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("WindCDF Interactive QC Tool")
        self.root.geometry("1400x900")
        
        # Data manager
        self.data_manager = DatasetManager()
        
        # Number of plots
        self.num_plots = 2
        
        # Build UI
        self._build_header()
        self._build_bottom_controls()  # Pack before main area to prevent hiding
        self._build_main_area()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _build_header(self) -> None:
        """Build the header controls."""
        header_frame = ttk.Frame(self.root)
        header_frame.pack(side="top", fill="x", padx=10, pady=5)
        
        # Load button
        load_btn = ttk.Button(header_frame, text="Load NetCDF File(s)",
                              command=self._load_files)
        load_btn.pack(side="left", padx=5)
        
        # Save button
        save_btn = ttk.Button(header_frame, text="Save NetCDF",
                              command=self._save_dataset)
        save_btn.pack(side="left", padx=5)
        
        # Separator
        ttk.Separator(header_frame, orient="vertical").pack(side="left", fill="y", 
                                                            padx=10, pady=2)
        
        # Number of plots selector
        ttk.Label(header_frame, text="Plots:").pack(side="left", padx=5)
        self.num_plots_var = tk.StringVar(value="2")
        plots_combo = ttk.Combobox(header_frame, textvariable=self.num_plots_var,
                                   values=["2", "3", "4"], width=3, state="readonly")
        plots_combo.pack(side="left", padx=2)
        
        apply_plots_btn = ttk.Button(header_frame, text="Apply",
                                     command=self._apply_num_plots)
        apply_plots_btn.pack(side="left", padx=5)
        
        # Separator
        ttk.Separator(header_frame, orient="vertical").pack(side="left", fill="y",
                                                            padx=10, pady=2)
        
        # QC flag dropdown
        ttk.Label(header_frame, text="QC Flag:").pack(side="left", padx=5)
        
        flag_options = [f"{val}: {QC_FLAGS[val][0]}" for val in sorted(QC_FLAGS.keys())]
        self.qc_flag_var = tk.StringVar(value=flag_options[0])
        flag_combo = ttk.Combobox(header_frame, textvariable=self.qc_flag_var,
                                  values=flag_options, width=20, state="readonly")
        flag_combo.pack(side="left", padx=2)
        
        # Apply Selection button
        apply_sel_btn = ttk.Button(header_frame, text="Apply Selection",
                                   command=self._apply_selection)
        apply_sel_btn.pack(side="left", padx=5)
        
        # Undo button
        undo_btn = ttk.Button(header_frame, text="Undo Last",
                              command=self._undo_last)
        undo_btn.pack(side="left", padx=5)
    
    def _build_main_area(self) -> None:
        """Build the main content area with tree and plots."""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)
        
        # Left panel - selection tree
        left_frame = ttk.LabelFrame(main_frame, text="Datasets / Variables / Series")
        left_frame.pack(side="left", fill="y", padx=(0, 5))
        
        self.selection_tree = SelectionTreeview(
            left_frame, 
            self._on_selection_change,
            self._on_color_change
        )
        self.selection_tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Right panel - plots
        right_frame = ttk.LabelFrame(main_frame, text="Time Series Plots")
        right_frame.pack(side="left", fill="both", expand=True)
        
        self.plot_canvas = QCPlotCanvas(right_frame, self.num_plots)
        self.plot_canvas.on_selection_callback = self._on_plot_selection
    
    def _build_bottom_controls(self) -> None:
        """Build the bottom control panel."""
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(side="bottom", fill="x", padx=10, pady=5)
        
        # Time slider
        time_frame = ttk.LabelFrame(bottom_frame, text="Time Range")
        time_frame.pack(side="top", fill="x", pady=2)
        
        self.time_slider = TimeSliderControl(time_frame, self._on_time_range_change)
        self.time_slider.pack(fill="x", padx=5, pady=5)
        
        # Zoom slider
        zoom_frame = ttk.LabelFrame(bottom_frame, text="Zoom")
        zoom_frame.pack(side="top", fill="x", pady=2)
        
        self.zoom_slider = ZoomSliderControl(zoom_frame, self._on_zoom_change)
        self.zoom_slider.pack(fill="x", padx=5, pady=5)
    
    def _load_files(self) -> None:
        """Load one or more NetCDF files."""
        filepaths = filedialog.askopenfilenames(
            title="Select NetCDF Files",
            filetypes=[("NetCDF Files", "*.nc *.nc4 *.netcdf"), ("All Files", "*.*")]
        )
        
        if not filepaths:
            return
        
        for filepath in filepaths:
            try:
                dataset_id = self.data_manager.load_dataset(filepath)
                
                # Get eligible variables
                variables = self.data_manager.get_eligible_variables(dataset_id)
                
                # Add to tree
                self.selection_tree.add_dataset(
                    dataset_id, variables,
                    lambda ds_id, var: self.data_manager.get_variable_series(ds_id, var)
                )
                
            except Exception as e:
                messagebox.showerror("Error Loading File", 
                                    f"Failed to load {filepath}:\n{str(e)}")
        
        # Update time bounds
        bounds = self.data_manager.get_time_bounds()
        if bounds:
            self.plot_canvas.set_time_bounds(*bounds)
            self.time_slider.set_time_bounds(*bounds)
    
    def _save_dataset(self) -> None:
        """Save a dataset to a NetCDF file."""
        if not self.data_manager.datasets:
            messagebox.showinfo("No Data", "No datasets to save.")
            return
        
        # If multiple datasets, ask which one
        dataset_ids = list(self.data_manager.datasets.keys())
        
        if len(dataset_ids) == 1:
            dataset_id = dataset_ids[0]
        else:
            # Create selection dialog
            dialog = tk.Toplevel(self.root)
            dialog.title("Select Dataset to Save")
            dialog.geometry("300x150")
            dialog.transient(self.root)
            dialog.grab_set()
            
            ttk.Label(dialog, text="Select dataset to save:").pack(pady=10)
            
            selected = tk.StringVar(value=dataset_ids[0])
            combo = ttk.Combobox(dialog, textvariable=selected, values=dataset_ids,
                                state="readonly", width=40)
            combo.pack(pady=5)
            
            result = [None]
            
            def on_ok():
                result[0] = selected.get()
                dialog.destroy()
            
            ttk.Button(dialog, text="OK", command=on_ok).pack(pady=10)
            
            dialog.wait_window()
            dataset_id = result[0]
            
            if dataset_id is None:
                return
        
        # Ask for save location
        filepath = filedialog.asksaveasfilename(
            title=f"Save {dataset_id}",
            defaultextension=".nc",
            filetypes=[("NetCDF Files", "*.nc"), ("All Files", "*.*")],
            initialfile=dataset_id
        )
        
        if not filepath:
            return
        
        try:
            self.data_manager.save_dataset(dataset_id, filepath)
            messagebox.showinfo("Success", f"Dataset saved to {filepath}")
        except Exception as e:
            messagebox.showerror("Error Saving File", str(e))
    
    def _apply_num_plots(self) -> None:
        """Apply the selected number of plots."""
        num = int(self.num_plots_var.get())
        self.num_plots = num
        self.plot_canvas.set_num_plots(num)
        self._refresh_plots()
    
    def _apply_selection(self) -> None:
        """Apply QC flag to selected time range."""
        # Get selection times
        selection = self.plot_canvas.get_selection_times()
        if selection is None:
            messagebox.showinfo("No Selection", 
                               "Please select a time range on a plot first.")
            return
        
        time_start, time_end = selection
        
        # Get QC flag value
        flag_str = self.qc_flag_var.get()
        flag_value = int(flag_str.split(":")[0])
        
        # Get QC-enabled series
        qc_series = self.selection_tree.get_qc_enabled_series()
        if not qc_series:
            messagebox.showinfo("No QC Series", 
                               "Please enable QC for at least one series.")
            return
        
        # Apply to all QC-enabled series
        for series_id in qc_series:
            self.data_manager.apply_qc_flag(series_id, time_start, time_end, flag_value)
        
        # Clear selection and refresh
        self.plot_canvas.clear_selection()
        self._refresh_plots()
    
    def _undo_last(self) -> None:
        """Undo the last QC operation."""
        affected = self.data_manager.undo_last()
        if affected is None:
            messagebox.showinfo("Nothing to Undo", "No operations to undo.")
            return
        
        self._refresh_plots()
    
    def _on_selection_change(self) -> None:
        """Handle changes to tree selection."""
        # Update plot assignments
        assignments = self.selection_tree.get_plot_assignments()
        
        for plot_idx, series_list in assignments.items():
            self.plot_canvas.plot_assignments[plot_idx] = series_list
        
        # Sync colors from tree to plot canvas
        self._sync_colors()
        
        self._refresh_plots()
    
    def _on_color_change(self, series_id: SeriesIdentifier, color: str) -> None:
        """Handle color change from tree."""
        self.plot_canvas.set_series_color(series_id, color)
        self._refresh_plots()
    
    def _sync_colors(self) -> None:
        """Sync colors from tree to plot canvas."""
        colors = self.selection_tree.get_series_colors()
        for series_id, color in colors.items():
            self.plot_canvas.set_series_color(series_id, color)
    
    def _on_plot_selection(self, xmin: float, xmax: float) -> None:
        """Handle time range selection on plots."""
        # Selection is stored in plot_canvas
        pass
    
    def _on_time_range_change(self, time_min: np.datetime64, 
                              time_max: np.datetime64) -> None:
        """Handle time range slider change."""
        self.plot_canvas.set_view_range(time_min, time_max)
    
    def _on_zoom_change(self, zoom_percent: float) -> None:
        """Handle zoom slider change."""
        self.time_slider.set_zoom(zoom_percent)
    
    def _refresh_plots(self) -> None:
        """Refresh all plots with current data."""
        self.plot_canvas.update_plots(self.data_manager)
    
    def _on_close(self) -> None:
        """Handle window close."""
        self.data_manager.close_all()
        self.root.destroy()


def main():
    """Entry point for the QC tool."""
    root = tk.Tk()
    _app = QCToolApp(root)  # noqa: F841
    root.mainloop()


if __name__ == "__main__":
    main()
