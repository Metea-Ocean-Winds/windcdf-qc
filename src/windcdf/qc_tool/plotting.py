"""Plotting functionality with LineCollection-based QC visualization."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Callable

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from matplotlib.widgets import SpanSelector

if TYPE_CHECKING:
    from windcdf.qc_tool.data_model import DatasetManager, SeriesIdentifier

from windcdf.qc_tool.data_model import QC_FLAGS


class QCPlotCanvas:
    """Matplotlib canvas with QC-aware plotting using LineCollection."""
    
    def __init__(self, master, num_plots: int = 2):
        self.master = master
        self.num_plots = num_plots
        self.figure: Figure | None = None
        self.canvas: FigureCanvasTkAgg | None = None
        self.axes: list[plt.Axes] = []
        
        # Series assignments: plot_index -> list of SeriesIdentifier
        self.plot_assignments: dict[int, list["SeriesIdentifier"]] = {
            i: [] for i in range(4)
        }
        
        # Line collections for each series
        self.line_collections: dict["SeriesIdentifier", dict] = {}
        
        # Series colors
        self.series_colors: dict["SeriesIdentifier", str] = {}
        
        # Span selectors for each plot
        self.span_selectors: list[SpanSelector] = []
        
        # Selection callback
        self.on_selection_callback: Callable[[float, float], None] | None = None
        
        # Current selection
        self.selection_start: float | None = None
        self.selection_end: float | None = None
        self.selection_patches: list = []
        
        # Time bounds
        self.full_time_min: np.datetime64 | None = None
        self.full_time_max: np.datetime64 | None = None
        self.view_time_min: np.datetime64 | None = None
        self.view_time_max: np.datetime64 | None = None
        
        self._create_figure(num_plots)
    
    def _create_figure(self, num_plots: int) -> None:
        """Create the matplotlib figure with specified number of plots."""
        self.num_plots = num_plots
        
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        
        self.figure = Figure(figsize=(12, 3 * num_plots), dpi=100)
        self.axes = []
        
        for i in range(num_plots):
            ax = self.figure.add_subplot(num_plots, 1, i + 1)
            ax.set_xlabel("Time")
            ax.set_ylabel("Value")
            ax.grid(True, alpha=0.3)
            self.axes.append(ax)
        
        self.figure.tight_layout()
        
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.master)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # Setup span selectors
        self._setup_span_selectors()
    
    def _setup_span_selectors(self) -> None:
        """Setup span selectors for time range selection."""
        self.span_selectors = []
        
        for ax in self.axes:
            span = SpanSelector(
                ax,
                self._on_span_select,
                "horizontal",
                useblit=True,
                props=dict(alpha=0.3, facecolor="blue"),
                interactive=True,
                drag_from_anywhere=True,
            )
            self.span_selectors.append(span)
    
    def _on_span_select(self, xmin: float, xmax: float) -> None:
        """Handle span selection event."""
        self.selection_start = xmin
        self.selection_end = xmax
        
        # Highlight selection on all plots
        self._draw_selection_highlight(xmin, xmax)
        
        if self.on_selection_callback:
            self.on_selection_callback(xmin, xmax)
    
    def _draw_selection_highlight(self, xmin: float, xmax: float) -> None:
        """Draw selection highlight on all plots."""
        # Remove old patches
        for patch in self.selection_patches:
            patch.remove()
        self.selection_patches = []
        
        # Add new patches
        for ax in self.axes:
            patch = ax.axvspan(xmin, xmax, alpha=0.2, color="blue")
            self.selection_patches.append(patch)
        
        self.canvas.draw_idle()
    
    def clear_selection(self) -> None:
        """Clear current selection."""
        for patch in self.selection_patches:
            patch.remove()
        self.selection_patches = []
        self.selection_start = None
        self.selection_end = None
        self.canvas.draw_idle()
    
    def set_num_plots(self, num_plots: int) -> None:
        """Change the number of plots."""
        if num_plots == self.num_plots:
            return
        
        # Store current assignments
        old_assignments = self.plot_assignments.copy()
        
        self._create_figure(num_plots)
        
        # Restore assignments that still fit
        for i in range(num_plots):
            if i in old_assignments:
                self.plot_assignments[i] = old_assignments[i]
    
    def assign_series_to_plot(
        self, series_id: "SeriesIdentifier", plot_index: int
    ) -> None:
        """Assign a series to a specific plot."""
        # Remove from any existing assignment
        for idx in self.plot_assignments:
            if series_id in self.plot_assignments[idx]:
                self.plot_assignments[idx].remove(series_id)
        
        # Add to new plot
        if plot_index < self.num_plots:
            self.plot_assignments[plot_index].append(series_id)
    
    def remove_series_from_plots(self, series_id: "SeriesIdentifier") -> None:
        """Remove a series from all plots."""
        for idx in self.plot_assignments:
            if series_id in self.plot_assignments[idx]:
                self.plot_assignments[idx].remove(series_id)
    
    def update_plots(self, data_manager: "DatasetManager") -> None:
        """Redraw all plots with current data."""
        self.line_collections.clear()
        
        for idx, ax in enumerate(self.axes):
            ax.clear()
            ax.set_xlabel("Time")
            ax.set_ylabel("Value")
            ax.grid(True, alpha=0.3)
            
            # Setup datetime formatting for x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M"))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            
            if idx not in self.plot_assignments:
                continue
            
            for series_id in self.plot_assignments[idx]:
                self._draw_series(ax, series_id, data_manager)
            
            ax.legend(loc="upper right", fontsize=8)
            
            # Rotate date labels for readability
            for label in ax.get_xticklabels():
                label.set_rotation(30)
                label.set_ha("right")
        
        # Apply time view limits using matplotlib dates
        if self.view_time_min is not None and self.view_time_max is not None:
            import pandas as pd
            view_min_mpl = mdates.date2num(pd.Timestamp(self.view_time_min))
            view_max_mpl = mdates.date2num(pd.Timestamp(self.view_time_max))
            for ax in self.axes:
                ax.set_xlim(view_min_mpl, view_max_mpl)
        
        self.figure.tight_layout()
        self.canvas.draw_idle()
        
        # Re-setup span selectors
        self._setup_span_selectors()
    
    def _draw_series(self, ax: plt.Axes, series_id: "SeriesIdentifier", 
                     data_manager: "DatasetManager") -> None:
        """Draw a single series with QC flag coloring using LineCollection."""
        import pandas as pd
        
        try:
            time, values, qc_flags = data_manager.get_series_data(series_id)
        except Exception as e:
            print(f"Error getting data for {series_id}: {e}")
            return
        
        # Convert time to matplotlib date format
        time_mpl = mdates.date2num([pd.Timestamp(t) for t in time])
        
        # Get or generate series color
        if series_id not in self.series_colors:
            self.series_colors[series_id] = self._generate_random_color()
        base_color = self.series_colors[series_id]
        
        # Create base line segments
        points = np.array([time_mpl, values]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        
        # Draw base line in series color
        base_line = LineCollection(segments, colors=base_color, linewidths=1.5, 
                                   label=series_id.get_display_name())
        ax.add_collection(base_line)
        
        # Create colored overlays for each QC flag (except 0 = good)
        collections = {"base": base_line}
        
        for flag_value, (meaning, color) in QC_FLAGS.items():
            if color is None:  # Skip "good" (no overlay)
                continue
            
            # Find segments where either endpoint has this flag
            mask = np.zeros(len(segments), dtype=bool)
            for i in range(len(segments)):
                if i < len(qc_flags) and qc_flags[i] == flag_value:
                    mask[i] = True
                if i + 1 < len(qc_flags) and qc_flags[i + 1] == flag_value:
                    mask[i] = True
            
            if np.any(mask):
                flagged_segments = segments[mask]
                flag_line = LineCollection(flagged_segments, colors=color, 
                                          linewidths=2.0, alpha=0.8)
                ax.add_collection(flag_line)
                collections[flag_value] = flag_line
        
        self.line_collections[series_id] = collections
        
        # Update axes limits
        ax.set_xlim(time_mpl.min(), time_mpl.max())
        
        # Compute y limits avoiding NaN
        valid_values = values[~np.isnan(values)]
        if len(valid_values) > 0:
            margin = (valid_values.max() - valid_values.min()) * 0.05
            ax.set_ylim(valid_values.min() - margin, valid_values.max() + margin)
    
    def _generate_random_color(self) -> str:
        """Generate a random hex color."""
        r = random.randint(50, 200)
        g = random.randint(50, 200)
        b = random.randint(50, 200)
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def get_series_color(self, series_id: "SeriesIdentifier") -> str:
        """Get the color for a series."""
        if series_id not in self.series_colors:
            self.series_colors[series_id] = self._generate_random_color()
        return self.series_colors[series_id]
    
    def set_series_color(self, series_id: "SeriesIdentifier", color: str) -> None:
        """Set the color for a series."""
        self.series_colors[series_id] = color
    
    def set_time_bounds(self, time_min: np.datetime64, time_max: np.datetime64) -> None:
        """Set the full time bounds."""
        self.full_time_min = time_min
        self.full_time_max = time_max
        self.view_time_min = time_min
        self.view_time_max = time_max
    
    def set_view_range(self, time_min: np.datetime64, time_max: np.datetime64) -> None:
        """Set the visible time range."""
        import pandas as pd
        
        self.view_time_min = time_min
        self.view_time_max = time_max
        
        view_min_mpl = mdates.date2num(pd.Timestamp(time_min))
        view_max_mpl = mdates.date2num(pd.Timestamp(time_max))
        
        for ax in self.axes:
            ax.set_xlim(view_min_mpl, view_max_mpl)
        
        self.canvas.draw_idle()
    
    def get_selection_times(self) -> tuple[np.datetime64, np.datetime64] | None:
        """Get the current selection as datetime64 values."""
        if self.selection_start is None or self.selection_end is None:
            return None
        
        # Convert from matplotlib date number to datetime64
        start_dt = mdates.num2date(self.selection_start)
        end_dt = mdates.num2date(self.selection_end)
        
        start = np.datetime64(start_dt.replace(tzinfo=None))
        end = np.datetime64(end_dt.replace(tzinfo=None))
        
        return start, end
