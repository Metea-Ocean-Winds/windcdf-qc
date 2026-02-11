import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os
import xarray as xr
import numpy as np
import random
import yaml
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.widgets import SpanSelector

from datamanager import DatasetManager
from selection_dialog import SelectionDialog


class WindCDF_GUI(tk.Frame):
    """Graphical User Interface for timer series plot and quality control of NetCDF datasets."""
    
    def __init__(self, master=None, num_panels: int | None = None, minsize: int | None = None, width: int | None = None):
        super().__init__(master)
        self.grid(sticky="nsew")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        
        self._manager = DatasetManager()
        self._user_selections: dict[str, dict] = {}  # source -> z -> [vars]
        self._plot_config: dict = {}  # (source, z, var) -> {color, panels: [bool, bool, bool]}
        self._last_loaded_dataset: str | None = None
        self._dataset_count: int = 0  # Track number of loaded datasets
        
        # Cache for split datasets: source -> {time: array, vars: {var: {z: array}}}
        self._source_data_cache: dict[str, dict] = {}
        
        # Store line references for efficient updates
        self._plot_lines: dict[tuple, list] = {}  # (source, z, var, panel_idx) -> [line, scatter]
        
        # Load settings
        self._settings = self._load_settings(None)
        # Override number of panels if provided via command line
        if num_panels is not None:
            self._num_panels = num_panels
        else:
            self._num_panels = self._settings.get("number of panels", 3)
        left_panel_settings = self._settings.get("left_panel", {})
        # Override left panel dimensions if provided via command line
        self._left_panel_minsize = minsize if minsize is not None else left_panel_settings.get("minsize", 180)
        self._left_panel_width = width if width is not None else left_panel_settings.get("width", 260)
        self._status_mapping_config = self._settings.get("status_mapping", {})
        

        # Y-range controls per panel (dynamic based on number of panels)
        self._y_lock_vars: list[tk.BooleanVar] = []
        self._y_min_vars: list[tk.StringVar] = []
        self._y_max_vars: list[tk.StringVar] = []
        
        # Time range controls
        self._time_min_num: float | None = None
        self._time_max_num: float | None = None
        self._window_var = tk.StringVar(value="1.0")
        
        # Selection & QC controls (dynamic based on number of panels)
        self._span_selectors: list[SpanSelector | None] = [None] * self._num_panels
        self._current_selection: tuple[float, float] | None = None
        self._selection_patches: list = [None] * self._num_panels
        self._status_var = tk.StringVar()
        
        # QC apply selection: (source, z, var) -> BooleanVar
        self._qc_apply_vars: dict[tuple, tk.BooleanVar] = {}
        
        # Undo state: source -> var -> z -> backup array
        self._last_qc_backup: dict[str, dict[str, dict]] = {}
        
        # Build status mapping for dropdown
        self._status_mapping = self._build_status_mapping()
        
        self._build_ui()
    
    def _load_settings(self, path: str | None) -> dict:
        """Load settings from YAML file or use defaults."""
        default_settings = {
            "number of panels": 3,
            "status_mapping": {
                3: {"label": "Pass", "marker": None, "description": "Data passed all quality checks"},
                2: {"label": "Pass after Process", "marker": None, "description": "Data passed after processing/correction"},
                -11: {"label": "Suspect", "marker": {"color": "grey", "edgecolor": "grey"}, "description": "Data automatically flagged as suspect"},
                -12: {"label": "Suspect", "marker": {"color": "grey", "edgecolor": "grey"}, "description": "Data manually flagged as suspect"},
                -21: {"label": "Fail", "marker": {"color": "black", "edgecolor": "black"}, "description": "Data automatically flagged as failed"},
                -22: {"label": "Fail", "marker": {"color": "black", "edgecolor": "black"}, "description": "Data manually flagged as failed"},
                -33: {"label": "To Be Fixed", "marker": {"color": "white", "edgecolor": "black"}, "description": "Data needs manual correction"},
                -34: {"label": "To Be Interpolated", "marker": {"color": "white", "edgecolor": "black"}, "description": "Data needs interpolation"},
            }
        }
        
        if path is None:
            # Try to load from default location
            default_path = os.path.join(os.path.dirname(__file__), "settings.yaml")
            if os.path.exists(default_path):
                path = default_path
        
        if path and os.path.exists(path):
            try:
                with open(path, "r") as f:
                    config = yaml.safe_load(f)
                    return config if config else default_settings
            except Exception as e:
                print(f"Warning: Could not load settings from {path}: {e}")
        
        return default_settings
    
    def _build_status_mapping(self) -> dict:
        """Build status mapping for dropdown from settings config."""
        mapping = {}
        for code, info in self._status_mapping_config.items():
            label = info.get("label", str(code))
            mapping[f"{label} ({code})"] = int(code)
        return mapping
    
    def _build_ui(self):
        """Build the main user interface."""
        main_container = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashwidth=5)
        main_container.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        left_panel = tk.Frame(main_container)
        main_container.add(left_panel, minsize=self._left_panel_minsize, width=self._left_panel_width)
        
        right_panel = tk.Frame(main_container)
        main_container.add(right_panel, minsize=400)
        
        self._build_left_panel(left_panel)
        self._build_plot_area(right_panel)
        
        # Set initial sash position after window is mapped
        self.after(10, lambda: main_container.sash_place(0, 260, 0))
    
    def _build_left_panel(self, parent):
        """Build the left control panel."""
        control_frame = tk.Frame(parent)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        self._load_btn = tk.Button(
            control_frame, 
            text="Load Dataset",
            command=self._load_dataset_from_file
        )
        self._load_btn.pack(side="left", padx=(0, 5))
        
        self._save_btn = tk.Button(
            control_frame,
            text="Save Dataset",
            command=self._save_dataset_to_file
        )
        self._save_btn.pack(side="left", padx=(0, 5))
        
        var_container = tk.Frame(parent)
        var_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        self._var_canvas = tk.Canvas(var_container)
        v_scrollbar = ttk.Scrollbar(var_container, orient="vertical", command=self._var_canvas.yview)
        h_scrollbar = ttk.Scrollbar(var_container, orient="horizontal", command=self._var_canvas.xview)
        
        self._var_inner_frame = tk.Frame(self._var_canvas)
        self._var_inner_frame.bind("<Configure>", lambda e: self._var_canvas.configure(
            scrollregion=self._var_canvas.bbox("all")
        ))
        
        self._var_canvas.create_window((0, 0), window=self._var_inner_frame, anchor="nw")
        self._var_canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        self._var_canvas.pack(side="left", fill="both", expand=True)
    
    def _build_plot_area(self, parent):
        """Build the matplotlib plot area."""
        # QC controls at very top
        self._build_qc_controls(parent)
        
        # Y-range controls frame
        self._build_y_controls(parent)
        
        # Create subplots dynamically based on number of panels
        self.fig, self.axes = plt.subplots(self._num_panels, 1, sharex=True, figsize=(10, 7))
        if self._num_panels == 1:
            self.axes = [self.axes]  # Make it iterable
        self.fig.subplots_adjust(left=0.08, bottom=0.07, right=0.97, top=0.98, hspace=0.2)
        
        for i, ax in enumerate(self.axes):
            ax.set_ylabel(f"Panel {i+1}")
            ax.grid(True)
        self.axes[-1].set_xlabel("Time")
        
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.toolbar = NavigationToolbar2Tk(self.canvas, parent)
        self.toolbar.update()
        
        # Time controls below toolbar
        self._build_time_controls(parent)
        
        # Initialize span selectors
        self._init_span_selectors()
        
        self.canvas.draw()
    
    def _build_qc_controls(self, parent):
        """Build QC status selection and apply controls."""
        qc_frame = tk.Frame(parent)
        qc_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
        
        tk.Label(qc_frame, text="QC Status:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        # Status dropdown
        self._status_combo = ttk.Combobox(
            qc_frame,
            textvariable=self._status_var,
            state="readonly",
            width=25,
            font=("Arial", 8)
        )
        self._status_combo["values"] = list(self._status_mapping.keys())
        if self._status_combo["values"]:
            self._status_combo.current(0)
        self._status_combo.pack(side=tk.LEFT, padx=5)
        
        # Apply button
        self._btn_apply_status = tk.Button(
            qc_frame,
            text="Apply to Selection",
            command=self._apply_status_to_selection,
            state="disabled",
            font=("Arial", 8)
        )
        self._btn_apply_status.pack(side=tk.LEFT, padx=5)
        
        # Undo button
        self._btn_undo = tk.Button(
            qc_frame,
            text="Undo Last",
            command=self._undo_last_change,
            state="disabled",
            font=("Arial", 8)
        )
        self._btn_undo.pack(side=tk.LEFT, padx=5)
        
        # Select All / Deselect All buttons for QC apply
        self._btn_select_all = tk.Button(
            qc_frame,
            text="Select All",
            command=self._select_all_for_qc,
            font=("Arial", 8)
        )
        self._btn_select_all.pack(side=tk.LEFT, padx=2)
        
        self._btn_deselect_all = tk.Button(
            qc_frame,
            text="Deselect All",
            command=self._deselect_all_for_qc,
            font=("Arial", 8)
        )
        self._btn_deselect_all.pack(side=tk.LEFT, padx=2)
        
        # Selection info label
        self._selection_lbl = tk.Label(qc_frame, text="", font=("Arial", 8), fg="gray")
        self._selection_lbl.pack(side=tk.LEFT, padx=10)
    
    def _build_y_controls(self, parent):
        """Build Y-range controls for each panel."""
        y_ctrl_frame = tk.Frame(parent)
        y_ctrl_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
        
        tk.Label(y_ctrl_frame, text="Y-range:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        for i in range(self._num_panels):
            # Initialize variables
            lock_var = tk.BooleanVar(value=False)
            min_var = tk.StringVar()
            max_var = tk.StringVar()
            
            self._y_lock_vars.append(lock_var)
            self._y_min_vars.append(min_var)
            self._y_max_vars.append(max_var)
            
            # Panel frame
            panel_frame = tk.Frame(y_ctrl_frame)
            panel_frame.pack(side=tk.LEFT, padx=(10, 5))
            
            tk.Label(panel_frame, text=f"P{i+1}:", font=("Arial", 8, "bold")).pack(side=tk.LEFT, padx=2)
            
            tk.Checkbutton(
                panel_frame,
                text="Lock",
                variable=lock_var,
                command=lambda idx=i: self._on_y_lock_toggle(idx),
                font=("Arial", 8)
            ).pack(side=tk.LEFT, padx=2)
            
            tk.Label(panel_frame, text="Min:", font=("Arial", 8)).pack(side=tk.LEFT, padx=(5, 2))
            tk.Entry(panel_frame, width=6, textvariable=min_var, font=("Arial", 8)).pack(side=tk.LEFT)
            
            tk.Label(panel_frame, text="Max:", font=("Arial", 8)).pack(side=tk.LEFT, padx=(5, 2))
            tk.Entry(panel_frame, width=6, textvariable=max_var, font=("Arial", 8)).pack(side=tk.LEFT)
            
            tk.Button(
                panel_frame,
                text="Set",
                command=lambda idx=i: self._apply_y_range(idx),
                font=("Arial", 8),
                width=3
            ).pack(side=tk.LEFT, padx=2)
    
    def _build_time_controls(self, parent):
        """Build time navigation and zoom controls."""
        time_ctrl = tk.Frame(parent)
        time_ctrl.pack(side=tk.TOP, fill=tk.X, pady=2)
        
        # Time position label
        tk.Label(time_ctrl, text="Time pos:", font=("Arial", 8)).pack(side=tk.LEFT, padx=2)
        
        # Left arrow
        self._btn_left = tk.Button(
            time_ctrl,
            text="◀",
            width=2,
            command=lambda: self._shift_time_window(-1),
            font=("Arial", 8)
        )
        self._btn_left.pack(side=tk.LEFT, padx=2)
        
        # Time position slider
        self._time_slider = tk.Scale(
            time_ctrl,
            from_=0,
            to=1000,
            orient=tk.HORIZONTAL,
            showvalue=False,
            command=self._on_time_slider_move,
            length=200
        )
        self._time_slider.set(0)
        self._time_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Right arrow
        self._btn_right = tk.Button(
            time_ctrl,
            text="▶",
            width=2,
            command=lambda: self._shift_time_window(+1),
            font=("Arial", 8)
        )
        self._btn_right.pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(time_ctrl, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Window % controls
        tk.Label(time_ctrl, text="Zoom %:", font=("Arial", 8)).pack(side=tk.LEFT, padx=2)
        
        self._window_slider = tk.Scale(
            time_ctrl,
            from_=1,
            to=100,
            orient=tk.HORIZONTAL,
            showvalue=True,
            command=self._on_window_slider_move,
            length=100
        )
        self._window_slider.set(100)
        self._window_slider.pack(side=tk.LEFT, padx=2)
        
        self._window_entry = tk.Entry(time_ctrl, width=6, textvariable=self._window_var, font=("Arial", 8))
        self._window_entry.pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            time_ctrl,
            text="Set",
            command=self._on_window_set,
            font=("Arial", 8),
            width=3
        ).pack(side=tk.LEFT, padx=2)
    
    # ---------- PLOT FORMATTING HELPERS ----------
    
    def _apply_datetime_formatting(self):
        """Apply datetime formatting to all axes."""
        for ax in self.axes:
            # Use custom date formatter with smaller font
            formatter = mdates.DateFormatter('%Y-%m-%d\n%H')
            ax.xaxis.set_major_formatter(formatter)
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_minor_locator(mdates.AutoDateLocator(minticks=2, maxticks=10))
            
            # Set smaller font size without rotation
            try:
                plt.setp(ax.xaxis.get_majorticklabels(), fontsize=8)
            except Exception:
                # If label formatting fails, continue anyway
                pass
    
    # ---------- QC SELECTION HELPERS ----------
    
    def _select_all_for_qc(self):
        """Select all variable-height combinations for QC apply."""
        for var in self._qc_apply_vars.values():
            var.set(True)
    
    def _deselect_all_for_qc(self):
        """Deselect all variable-height combinations for QC apply."""
        for var in self._qc_apply_vars.values():
            var.set(False)
    
    # ---------- SPAN SELECTION ----------
    
    def _init_span_selectors(self):
        """Initialize span selectors for each panel."""
        for i, ax in enumerate(self.axes):
            if self._span_selectors[i] is not None:
                self._span_selectors[i].disconnect_events()
            
            self._span_selectors[i] = SpanSelector(
                ax,
                lambda tmin, tmax, idx=i: self._on_select_span(idx, tmin, tmax),
                "horizontal",
                useblit=True,
                interactive=True,
            )
    
    def _on_select_span(self, panel_idx: int, tmin: float, tmax: float):
        """Handle span selection on a panel."""
        self._current_selection = (tmin, tmax)
        
        # Update selection info label
        try:
            dt1 = mdates.num2date(tmin)
            dt2 = mdates.num2date(tmax)
            self._selection_lbl.config(
                text=f"Selected: {dt1.strftime('%Y-%m-%d %H:%M')} → {dt2.strftime('%Y-%m-%d %H:%M')}"
            )
        except Exception:
            self._selection_lbl.config(text=f"Selected: {tmin:.2f} → {tmax:.2f}")
        
        # Clear previous selection patches
        for i, patch in enumerate(self._selection_patches):
            if patch is not None:
                try:
                    patch.remove()
                except Exception:
                    pass
                self._selection_patches[i] = None
        
        # Draw highlight on all panels
        for i, ax in enumerate(self.axes):
            self._selection_patches[i] = ax.axvspan(
                tmin, tmax, alpha=0.3, color="yellow"
            )
        
        # Enable apply button
        self._btn_apply_status.config(state="normal")
        
        self.canvas.draw_idle()
    
    def _clear_selection(self):
        """Clear the current selection."""
        self._current_selection = None
        self._selection_lbl.config(text="")
        
        # Remove yellow highlight patches
        for i, patch in enumerate(self._selection_patches):
            if patch is not None:
                try:
                    patch.remove()
                except Exception:
                    pass
                self._selection_patches[i] = None
        
        # Clear the SpanSelector's visible selection on all panels
        for i, selector in enumerate(self._span_selectors):
            if selector is not None:
                selector.set_visible(False)
                selector.update()
        
        self._btn_apply_status.config(state="disabled")
        self.canvas.draw_idle()
    
    # ---------- QC STATUS APPLICATION ----------
    
    def _apply_status_to_selection(self):
        """Apply the selected QC status to selected variables in the selection."""
        if self._current_selection is None:
            messagebox.showwarning("No Selection", "Please select a time range first.")
            return
        
        if not self._plot_lines:
            messagebox.showwarning("No Data", "No variables are currently plotted.")
            return
        
        tmin, tmax = self._current_selection
        status_code = self._status_mapping[self._status_var.get()]
        
        # Get all active (source, z, var) combinations that are:
        # 1. Being plotted (at least one panel checked)
        # 2. Selected for QC apply (checkbox checked)
        active_keys = set()
        for (source, z, var), config in self._plot_config.items():
            if var.endswith("_qcflag"):
                continue
            if not any(config["panels"]):
                continue
            # Check if selected for QC apply
            key = (source, z, var)
            if key in self._qc_apply_vars and self._qc_apply_vars[key].get():
                active_keys.add(key)
        
        if not active_keys:
            messagebox.showwarning("No Variables Selected", 
                "No variables are selected for QC apply.\nCheck the 'QC' checkbox for variables you want to modify.")
            return
        
        # Backup current QC state
        self._last_qc_backup.clear()
        
        changes_made = 0
        
        for source, z, var in active_keys:
            qc_var = f"{var}_qcflag"
            
            # Check if QC data exists in cache
            if source not in self._source_data_cache:
                continue
            
            source_cache = self._source_data_cache[source]
            
            if qc_var not in source_cache["vars"] or z not in source_cache["vars"][qc_var]:
                # Create QC array if it doesn't exist
                if var in source_cache["vars"] and z in source_cache["vars"][var]:
                    data_shape = source_cache["vars"][var][z].shape
                    if qc_var not in source_cache["vars"]:
                        source_cache["vars"][qc_var] = {}
                    source_cache["vars"][qc_var][z] = np.ones(data_shape, dtype=int)  # Default to 1 (Auto-Pass)
            
            if qc_var not in source_cache["vars"] or z not in source_cache["vars"][qc_var]:
                continue
            
            # Backup
            if source not in self._last_qc_backup:
                self._last_qc_backup[source] = {}
            if var not in self._last_qc_backup[source]:
                self._last_qc_backup[source][var] = {}
            
            self._last_qc_backup[source][var][z] = source_cache["vars"][qc_var][z].copy()
            
            # Get time array and find indices in selection
            time = source_cache["time"]
            
            if np.issubdtype(time.dtype, np.datetime64):
                tnum = mdates.date2num(pd.to_datetime(time))
            else:
                tnum = time.astype(float)
            
            mask = (tnum >= tmin) & (tnum <= tmax)
            
            if mask.any():
                source_cache["vars"][qc_var][z][mask] = status_code
                changes_made += mask.sum()
        
        if changes_made > 0:
            self._btn_undo.config(state="normal")
            
            # Update the plots to show new QC markers
            self._refresh_qc_markers()
    
        self._clear_selection()
    
    def _undo_last_change(self):
        """Undo the last QC change."""
        if not self._last_qc_backup:
            messagebox.showinfo("Nothing to Undo", "No previous QC change to undo.")
            return
        
        # Restore from backup
        for source, vars_dict in self._last_qc_backup.items():
            if source not in self._source_data_cache:
                continue
            
            source_cache = self._source_data_cache[source]
            
            for var, z_dict in vars_dict.items():
                qc_var = f"{var}_qc_flag"
                
                if qc_var not in source_cache["vars"]:
                    continue
                
                for z, backup_data in z_dict.items():
                    source_cache["vars"][qc_var][z] = backup_data
        
        self._last_qc_backup.clear()
        self._btn_undo.config(state="disabled")
        
        # Refresh plots
        self._refresh_qc_markers()
        
        messagebox.showinfo("Undo Complete", "Last QC change has been undone.")
    
    def _refresh_qc_markers(self):
        """Refresh QC markers on all plots without full redraw."""
        # Save current view limits
        xlim = self.axes[0].get_xlim()
        ylims = [ax.get_ylim() for ax in self.axes]
        
        # Update only the scatter plots (QC markers) without clearing lines
        for line_key, artists in self._plot_lines.items():
            source, z, var, panel_idx = line_key
            
            # Remove old scatter if exists
            if len(artists) > 1 and artists[1] is not None:
                artists[1].remove()
                artists[1] = None
            # Remove additional scatters if they exist
            for i in range(2, len(artists)):
                if artists[i] is not None:
                    artists[i].remove()
            # Reset to just line and one scatter placeholder
            self._plot_lines[line_key] = [artists[0], None]
            artists = self._plot_lines[line_key]
            
            # Get updated QC data
            cached = self._get_cached_data(source, z, var)
            if cached is None:
                continue
            
            time, data, qc_data = cached
            
            # Add new scatters based on QC values
            if qc_data is not None:
                scatters = self._create_qc_scatters(self.axes[panel_idx], time, data, qc_data)
                if scatters:
                    artists[1] = scatters[0] if scatters else None
                    # Store additional scatters
                    self._plot_lines[line_key] = [artists[0]] + scatters
        
        # Restore view limits
        for ax in self.axes:
            ax.set_xlim(xlim)
        for i, ax in enumerate(self.axes):
            ax.set_ylim(ylims[i])
        
        self.canvas.draw_idle()
    
    def _create_qc_scatters(self, ax, time, data, qc_data):
        """Create scatter plots for different QC status categories based on settings."""
        scatters = []
        
        # Group QC codes by their marker style
        marker_groups = {}
        for code, info in self._status_mapping_config.items():
            marker = info.get("marker")
            if marker is None:
                continue
            
            # Create a hashable key from marker properties
            color = marker.get("color", "black")
            edgecolor = marker.get("edgecolor", color)
            marker_key = (color, edgecolor)
            
            if marker_key not in marker_groups:
                marker_groups[marker_key] = []
            marker_groups[marker_key].append(int(code))
        
        # Create scatter plots for each marker group
        for (color, edgecolor), codes in marker_groups.items():
            mask = np.isin(qc_data, codes)
            if mask.any():
                scatter = ax.scatter(
                    time[mask], 
                    data[mask],
                    color=color,
                    edgecolors=edgecolor,
                    linewidths=0.5 if color != edgecolor else 0,
                    s=3,
                    zorder=5
                )
                scatters.append(scatter)
        
        return scatters
    
    # ---------- Y-RANGE METHODS ----------
    
    def _on_y_lock_toggle(self, panel_idx: int):
        """Handle toggling of the 'Lock y-range' checkbox for a panel."""
        locked = self._y_lock_vars[panel_idx].get()
        ax = self.axes[panel_idx]
        
        if locked:
            # Capture current y-limits when locking
            ymin, ymax = ax.get_ylim()
            if not self._y_min_vars[panel_idx].get():
                self._y_min_vars[panel_idx].set(f"{ymin:.4g}")
            if not self._y_max_vars[panel_idx].get():
                self._y_max_vars[panel_idx].set(f"{ymax:.4g}")
    
    def _apply_y_range(self, panel_idx: int):
        """Apply manual y-limits for a panel and lock them."""
        try:
            ymin = float(self._y_min_vars[panel_idx].get())
            ymax = float(self._y_max_vars[panel_idx].get())
        except ValueError:
            messagebox.showwarning("Invalid Input", f"Invalid y-limits for Panel {panel_idx + 1}")
            return
        
        if ymin >= ymax:
            messagebox.showwarning("Invalid Input", "Min must be less than Max")
            return
        
        self._y_lock_vars[panel_idx].set(True)
        ax = self.axes[panel_idx]
        ax.set_ylim(ymin, ymax)
        self.canvas.draw_idle()
    
    def _apply_locked_y_ranges(self):
        """Apply all locked y-ranges to their respective panels."""
        for i in range(self._num_panels):
            if self._y_lock_vars[i].get():
                try:
                    ymin = float(self._y_min_vars[i].get())
                    ymax = float(self._y_max_vars[i].get())
                    self.axes[i].set_ylim(ymin, ymax)
                except ValueError:
                    pass
    
    # ---------- TIME RANGE METHODS ----------
    
    def _compute_time_bounds(self):
        """Compute global time bounds in Matplotlib date numbers from cached data."""
        if not self._source_data_cache:
            return
        
        all_times = []
        for source_cache in self._source_data_cache.values():
            time = source_cache.get("time")
            if time is not None:
                # Time should already be in matplotlib date numbers from _preextract_dataset
                all_times.append(time)
        
        if not all_times:
            return
        
        # Combine all times
        combined_time = np.concatenate(all_times)
        
        self._time_min_num = float(np.min(combined_time))
        self._time_max_num = float(np.max(combined_time))
    
    def _get_current_window_span(self) -> float | None:
        """Return the current x window span from panel 1 (axes[0])."""
        if self._time_min_num is None or self._time_max_num is None:
            self._compute_time_bounds()
        if self._time_min_num is None or self._time_max_num is None:
            return None
        
        span_global = self._time_max_num - self._time_min_num
        if span_global <= 0:
            return None
        
        x0, x1 = self.axes[0].get_xlim()
        window_span = x1 - x0
        if window_span <= 0 or window_span > span_global:
            window_span = span_global
        return window_span
    
    def _update_time_slider_from_axes(self):
        """Update the time slider based on the current x-limits of panel 1."""
        if self._time_min_num is None or self._time_max_num is None:
            self._compute_time_bounds()
        if self._time_min_num is None or self._time_max_num is None:
            return
        
        span_global = self._time_max_num - self._time_min_num
        if span_global <= 0:
            return
        
        x0, x1 = self.axes[0].get_xlim()
        window_span = x1 - x0
        if window_span <= 0 or window_span >= span_global:
            self._time_slider.set(0)
            return
        
        denom = span_global - window_span
        if denom <= 0:
            self._time_slider.set(0)
            return
        
        pos = (x0 - self._time_min_num) / denom
        pos = max(0.0, min(1.0, pos))
        self._time_slider.set(int(pos * 1000))
    
    def _update_window_controls_from_axes(self):
        """Sync window slider and entry with current window width."""
        if self._time_min_num is None or self._time_max_num is None:
            self._compute_time_bounds()
        if self._time_min_num is None or self._time_max_num is None:
            return
        
        span_global = self._time_max_num - self._time_min_num
        if span_global <= 0:
            return
        
        x0, x1 = self.axes[0].get_xlim()
        window_span = x1 - x0
        if window_span <= 0:
            return
        
        frac = window_span / span_global
        frac = max(1e-6, min(1.0, frac))
        percent = frac * 100.0
        
        self._window_slider.set(int(min(max(percent, 1.0), 100.0)))
        self._window_var.set(f"{frac:.4g}")
    
    def _on_time_slider_move(self, value):
        """Move the visible time window along the time axis, keeping current window width."""
        # Skip if no data loaded yet
        if not self._source_data_cache:
            return
        
        if self._time_min_num is None or self._time_max_num is None:
            self._compute_time_bounds()
            if self._time_min_num is None:
                return
        
        span_global = self._time_max_num - self._time_min_num
        if span_global <= 0:
            return
        
        window_span = self._get_current_window_span()
        if window_span is None:
            return
        window_span = max(1e-9, min(window_span, span_global))
        
        pos = float(value) / 1000.0
        pos = max(0.0, min(1.0, pos))
        
        if span_global == window_span:
            left = self._time_min_num
        else:
            left = self._time_min_num + pos * (span_global - window_span)
        right = left + window_span
        
        for ax in self.axes:
            ax.set_xlim(left, right)
        
        # Update datetime formatting for new time range
        self._apply_datetime_formatting()
        self._apply_locked_y_ranges()
        self.canvas.draw_idle()
    
    def _shift_time_window(self, direction: int):
        """
        Shift the current time window left/right.
        direction = -1 for left, +1 for right.
        Step = 25% of current window width.
        """
        # Skip if no data loaded
        if not self._source_data_cache:
            return
        
        if self._time_min_num is None or self._time_max_num is None:
            self._compute_time_bounds()
            if self._time_min_num is None:
                return
        
        span_global = self._time_max_num - self._time_min_num
        if span_global <= 0:
            return
        
        x0, x1 = self.axes[0].get_xlim()
        window_span = x1 - x0
        if window_span <= 0 or window_span > span_global:
            window_span = span_global
        
        step = window_span * 0.25 * direction
        
        left = x0 + step
        right = left + window_span
        
        # Clamp to bounds
        if left < self._time_min_num:
            left = self._time_min_num
            right = left + window_span
        if right > self._time_max_num:
            right = self._time_max_num
            left = right - window_span
        
        for ax in self.axes:
            ax.set_xlim(left, right)
        
        # Update datetime formatting for new time range
        self._apply_datetime_formatting()
        self._update_time_slider_from_axes()
        self._update_window_controls_from_axes()
        self._apply_locked_y_ranges()
        self.canvas.draw_idle()
    
    def _apply_window_fraction(self, frac: float):
        """Apply a new window width (fraction of global span) around current center."""
        if self._time_min_num is None or self._time_max_num is None:
            self._compute_time_bounds()
            if self._time_min_num is None:
                return
        
        span_global = self._time_max_num - self._time_min_num
        if span_global <= 0:
            return
        
        x0, x1 = self.axes[0].get_xlim()
        center = 0.5 * (x0 + x1)
        
        window_span = span_global * frac
        if window_span <= 0:
            return
        if window_span > span_global:
            window_span = span_global
        
        left = center - window_span / 2.0
        right = center + window_span / 2.0
        
        # Clamp to bounds
        if left < self._time_min_num:
            left = self._time_min_num
            right = left + window_span
        if right > self._time_max_num:
            right = self._time_max_num
            left = right - window_span
        
        for ax in self.axes:
            ax.set_xlim(left, right)
        
        # Update datetime formatting for new time range
        self._apply_datetime_formatting()
        self._update_time_slider_from_axes()
        self._update_window_controls_from_axes()
        self._apply_locked_y_ranges()
        self.canvas.draw_idle()
    
    def _on_window_slider_move(self, value):
        """Slider callback: value = 1..100 (% of full span)."""
        # Skip if no data loaded yet
        if not self._source_data_cache:
            return
        
        try:
            percent = float(value)
        except ValueError:
            return
        frac = max(1e-6, min(percent / 100.0, 1.0))
        self._apply_window_fraction(frac)
    
    def _on_window_set(self):
        """
        Entry + Set button:
        - If value <= 1, treat as fraction (e.g. 0.001 = 0.1%).
        - If value > 1, treat as percent (e.g. 10 = 10%).
        """
        # Skip if no data loaded
        if not self._source_data_cache:
            return
        
        text = self._window_var.get().strip()
        try:
            val = float(text)
        except ValueError:
            messagebox.showwarning("Invalid Input", "Invalid window value (use e.g. 0.001 or 10).")
            return
        
        if val <= 0:
            messagebox.showwarning("Invalid Input", "Window value must be > 0.")
            return
        
        if val <= 1.0:
            frac = val
        else:
            frac = val / 100.0
        
        frac = max(1e-6, min(frac, 1.0))
        percent = frac * 100.0
        
        self._window_slider.set(int(min(max(percent, 1.0), 100.0)))
        self._window_var.set(f"{frac:.4g}")
        
        self._apply_window_fraction(frac)
    
    # ---------- DATASET LOADING ----------
    
    def _load_dataset_from_file(self):
        """Open file dialog, load dataset, and show selection dialog."""
        filepath = filedialog.askopenfilename(
            title="Select NetCDF Dataset",
            filetypes=[
                ("NetCDF files", "*.nc"),
                ("All files", "*.*")
            ]
        )
        
        if not filepath:
            return
        
        try:
            ds = xr.load_dataset(filepath)
            identifier = os.path.splitext(os.path.basename(filepath))[0]
            self.register_dataset(ds, identifier)
            self._last_loaded_dataset = identifier
            self._show_selection_dialog()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load dataset:\n{e}")
    def _save_dataset_to_file(self):
        """Open dialog to select dataset and save it with QC modifications."""
        # Get list of loaded datasets
        dataset_names = list(self._manager.datasets.keys())
        
        if not dataset_names:
            messagebox.showwarning("No Datasets", "No datasets are loaded to save.")
            return
        
        # If only one dataset, use it directly
        if len(dataset_names) == 1:
            selected_dataset = dataset_names[0]
        else:
            # Show selection dialog for multiple datasets
            selected_dataset = self._show_dataset_selection_dialog(dataset_names)
            if selected_dataset is None:
                return
        
        # Get save file path
        filepath = filedialog.asksaveasfilename(
            title="Save Dataset",
            defaultextension=".nc",
            initialfile=f"{selected_dataset}_qced.nc",
            filetypes=[
                ("NetCDF files", "*.nc"),
                ("All files", "*.*")
            ]
        )
        
        if not filepath:
            return
        
        try:
            self._save_dataset_with_qc(selected_dataset, filepath)
            messagebox.showinfo("Success", f"Dataset saved to:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save dataset:\n{e}")
    
    def _show_dataset_selection_dialog(self, dataset_names: list) -> str | None:
        """Show a dialog to select which dataset to save."""
        dialog = tk.Toplevel(self)
        dialog.title("Select Dataset to Save")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()
        
        result = {"selected": None}
        
        tk.Label(dialog, text="Select dataset to save:", font=("Arial", 10)).pack(pady=10)
        
        selected_var = tk.StringVar(value=dataset_names[0])
        combo = ttk.Combobox(
            dialog,
            textvariable=selected_var,
            values=dataset_names,
            state="readonly",
            width=30
        )
        combo.pack(pady=5)
        
        def on_ok():
            result["selected"] = selected_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="OK", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)
        
        # Center dialog on parent
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        self.wait_window(dialog)
        return result["selected"]
    
    def _save_dataset_with_qc(self, dataset_name: str, filepath: str):
        """Save dataset with updated QC flags from cache."""
        # Get the original dataset
        ds = self._manager.datasets[dataset_name].copy(deep=True)
        ds_info = self._manager.get_dataset_info(dataset_name)
        shape_type = ds_info["shape_type"]
        series_dim = ds_info["series_dim"]
        source_dim = ds_info["source_dim"]
        
        # Get source values based on structure
        if shape_type == "time_plus_2" and source_dim:
            sources = ds[source_dim].values.tolist()
        elif "source" in ds.attrs:
            sources = [ds.attrs["source"]]
        else:
            sources = [dataset_name]
        
        # Get series values based on structure
        if series_dim and series_dim in ds.dims:
            series_values = ds[series_dim].values.tolist()
        else:
            series_values = ["all"]
        
        # Update QC flags from cache
        for source in sources:
            if source not in self._source_data_cache:
                continue
            
            source_cache = self._source_data_cache[source]
            
            for var_name, series_dict in source_cache["vars"].items():
                if not var_name.endswith("_qcflag"):
                    continue
                
                # Check if this QC variable exists in the dataset
                if var_name not in ds.data_vars:
                    # Create new QC variable in dataset
                    base_var = var_name.replace("_qcflag", "")
                    if base_var in ds.data_vars:
                        # Create with same dimensions as base variable
                        base_dims = ds[base_var].dims
                        shape = ds[base_var].shape
                        qc_data = np.ones(shape, dtype=int)
                        ds[var_name] = (base_dims, qc_data)
                
                if var_name not in ds.data_vars:
                    continue
                
                # Update values from cache
                for series_val, qc_array in series_dict.items():
                    try:
                        dims = ds[var_name].dims
                        
                        if shape_type == "time_only":
                            ds[var_name].values[:] = qc_array
                        elif shape_type == "time_plus_1":
                            if series_val == "all":
                                ds[var_name].values[:] = qc_array
                            else:
                                series_idx = list(ds[series_dim].values).index(series_val)
                                if series_dim == dims[0]:
                                    ds[var_name].values[series_idx, :] = qc_array
                                else:
                                    ds[var_name].values[:, series_idx] = qc_array
                        else:  # time_plus_2
                            source_idx = list(ds[source_dim].values).index(source)
                            series_idx = list(ds[series_dim].values).index(series_val)
                            
                            # Determine dimension order and assign
                            dim_order = {d: i for i, d in enumerate(dims)}
                            if source_dim in dim_order and series_dim in dim_order:
                                # Build slice tuple based on dimension order
                                slices = [slice(None)] * len(dims)
                                slices[dim_order[source_dim]] = source_idx
                                slices[dim_order[series_dim]] = series_idx
                                ds[var_name].values[tuple(slices)] = qc_array
                    except (ValueError, IndexError) as e:
                        print(f"Warning: Could not update {var_name} at {series_val}: {e}")
        
        # Add metadata about QC modification
        ds.attrs["qc_modified"] = pd.Timestamp.now().isoformat()
        ds.attrs["qc_tool"] = "WindCDF 0.1.0"
        
        # Save to file
        ds.to_netcdf(filepath)
            
    def register_dataset(self, ds: xr.Dataset, identifier: str):
        """Register a dataset using the DatasetManager."""
        try:
            self._manager.add_dataset(identifier, ds)
            self._last_loaded_dataset = identifier
            self._dataset_count += 1
            
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
    
    def _preextract_dataset(self, ds, dataset_name: str) -> None:
        """Pre-extract dataset information based on its structure."""
        ds_info = self._manager.get_dataset_info(dataset_name)
        shape_type = ds_info["shape_type"]
        series_dim = ds_info["series_dim"]
        source_dim = ds_info["source_dim"]
        
        if shape_type == "time_only":
            # No extra dimensions - single series per variable
            # Use source from global attributes
            source_name = ds.attrs.get("source", dataset_name)
            series_values = ["all"]
            source_values = [source_name]
        elif shape_type == "time_plus_1":
            # One extra dimension - check if it's "source"
            if series_dim == "source":
                # Split by source, series is always "all"
                series_values = ["all"]
                source_values = [self._manager._to_python_type(v) for v in ds[series_dim].values]
            else:
                # Normal series dimension
                series_values = [self._manager._to_python_type(v) for v in ds[series_dim].values]
                # Use dataset name or source attribute instead of "default"
                source_name = ds.attrs.get("source", dataset_name)
                source_values = [source_name]
        else:  # time_plus_2
            # Two extra dimensions - series_dim and source_dim
            series_values = [self._manager._to_python_type(v) for v in ds[series_dim].values]
            source_values = [self._manager._to_python_type(v) for v in ds[source_dim].values]
        
        # Extract data into cache based on structure
        time_values = ds[self._manager.time_dim].values
        
        # Convert time to matplotlib date numbers if needed
        if np.issubdtype(time_values.dtype, np.datetime64):
            # Already datetime, convert to matplotlib date numbers
            time_values = mdates.date2num(pd.to_datetime(time_values))
        elif np.issubdtype(time_values.dtype, np.number):
            # Numeric time - check if it looks like Unix timestamps
            # If values are large (> year 1900 in seconds), treat as Unix timestamps
            if time_values.size > 0:
                min_val = np.min(time_values)
                
                # Check if it looks like Unix timestamp (after 1900) or days since reference
                if min_val > 0 and min_val < 1e6:  # Likely days since reference date
                    # Try to use xarray time coordinate attributes for reference
                    time_coord = ds.coords.get(self._manager.time_dim)
                    if time_coord is not None:
                        # Try to decode time using xarray's time handling
                        try:
                            decoded_time = pd.to_datetime(time_coord.values)
                            time_values = mdates.date2num(decoded_time)
                        except Exception as e:
                            # Fallback: assume days since 1900-01-01
                            reference_date = pd.Timestamp('1900-01-01')
                            decoded_time = reference_date + pd.to_timedelta(time_values, unit='D')
                            time_values = mdates.date2num(decoded_time)
                    else:
                        # Fallback: assume days since 1900-01-01
                        reference_date = pd.Timestamp('1900-01-01')
                        decoded_time = reference_date + pd.to_timedelta(time_values, unit='D')
                        time_values = mdates.date2num(decoded_time)
                elif min_val >= 1e9:  # Likely Unix timestamp in seconds
                    decoded_time = pd.to_datetime(time_values, unit='s')
                    time_values = mdates.date2num(decoded_time)
                else:
                    # Could be days since Unix epoch or other format
                    # Try as days since 1970-01-01
                    try:
                        decoded_time = pd.to_datetime(time_values, unit='D', origin='unix')
                        time_values = mdates.date2num(decoded_time)
                    except Exception:
                        # Last fallback: treat as matplotlib date numbers already
                        pass
        
        for source in source_values:
            if source not in self._source_data_cache:
                self._source_data_cache[source] = {"time": time_values, "vars": {}}
            else:
                self._source_data_cache[source]["time"] = time_values
            
            for var in ds.data_vars:
                if var not in self._source_data_cache[source]["vars"]:
                    self._source_data_cache[source]["vars"][var] = {}
                
                for series_val in series_values:
                    if shape_type == "time_only":
                        data = ds[var].values
                        self._source_data_cache[source]["vars"][var]["all"] = data
                    elif shape_type == "time_plus_1":
                        if series_dim == "source":
                            # Extract data for this source
                            try:
                                data = ds[var].sel({series_dim: source}).values
                                self._source_data_cache[source]["vars"][var]["all"] = data
                            except Exception:
                                pass
                        else:
                            # Normal series extraction
                            try:
                                data = ds[var].sel({series_dim: series_val}).values
                                self._source_data_cache[source]["vars"][var][series_val] = data
                            except Exception:
                                pass
                    else:  # time_plus_2
                        try:
                            data = ds[var].sel({source_dim: source, series_dim: series_val}).values
                            self._source_data_cache[source]["vars"][var][series_val] = data
                        except Exception:
                            pass

        # Update global time bounds after caching
        self._compute_time_bounds()

    def _get_source_z_vars_for_dataset(self, identifier: str) -> dict:
        """Get source -> z -> vars dict for a specific dataset only."""
        if identifier not in self._manager.datasets:
            return {}
        return self._manager.get_nested_dict(identifier)
    
    def _get_qc_flag_map_for_dataset(self, identifier: str) -> dict:
        """Get QC flag map for a specific dataset only."""
        if identifier not in self._manager.datasets:
            return {}
        return self._manager.get_vars_with_qc_flags(identifier)
    
    def _show_selection_dialog(self):
        """Open the selection dialog window for the last loaded dataset only."""
        if self._last_loaded_dataset is None:
            return
        
        source_z_vars = self._get_source_z_vars_for_dataset(self._last_loaded_dataset)
        qc_map = self._get_qc_flag_map_for_dataset(self._last_loaded_dataset)
        
        if not source_z_vars:
            messagebox.showinfo("Info", "No valid variables found in dataset")
            return
        
        # Show clip option only for second and subsequent datasets
        show_clip = self._dataset_count > 1
        
        SelectionDialog(
            self, 
            source_z_vars, 
            qc_map, 
            self._handle_selection,
            show_clip_option=show_clip,
            dataset_name=self._last_loaded_dataset
        )
    
    def _handle_selection(self, chosen_items: dict, clip_to_range: bool = False):
        """Process the user's selection and update left panel."""
        # Apply clipping if requested
        if clip_to_range and self._last_loaded_dataset:
            self._apply_time_clipping(self._last_loaded_dataset)
        
        # Pre-extract data after potential clipping
        if self._last_loaded_dataset:
            ds = self._manager.datasets[self._last_loaded_dataset]
            self._preextract_dataset(ds, self._last_loaded_dataset)
        
        for source, z_vars in chosen_items.items():
            if source not in self._user_selections:
                self._user_selections[source] = {}
            for z, var_list in z_vars.items():
                if z not in self._user_selections[source]:
                    self._user_selections[source][z] = []
                for var in var_list:
                    if var not in self._user_selections[source][z]:
                        self._user_selections[source][z].append(var)
                        key = (source, z, var)
                        if key not in self._plot_config:
                            self._plot_config[key] = {
                                "color": self._random_color(),
                                "panels": [False] * self._num_panels
                            }
        
        self._rebuild_variable_panel()
    
    def _apply_time_clipping(self, identifier: str):
        """Clip a dataset to the reference time range and update it in the manager."""
        try:
            clipped_ds = self._manager.clip_to_time_range(identifier)
            # Replace the dataset with clipped version
            self._manager.datasets[identifier] = clipped_ds
            
            # Regenerate nested dict for clipped dataset
            ds_info = self._manager._dataset_info[identifier]
            self._manager._nested_dicts[identifier] = self._manager._generate_nested_dict(clipped_ds, ds_info, identifier)
            
        except Exception as e:
            messagebox.showwarning("Clipping Warning", f"Could not clip dataset: {e}")
    
    def _get_cached_data(self, source: str, z, var: str) -> tuple[np.ndarray, np.ndarray, np.ndarray | None] | None:
        """Get pre-extracted data from cache."""
        if source not in self._source_data_cache:
            return None
        
        source_cache = self._source_data_cache[source]
        
        if var not in source_cache["vars"] or z not in source_cache["vars"][var]:
            return None
        
        time = source_cache["time"]
        data = source_cache["vars"][var][z]
        
        # Get QC data if available
        qc_var = f"{var}_qcflag"
        qc_data = None
        if qc_var in source_cache["vars"] and z in source_cache["vars"][qc_var]:
            qc_data = source_cache["vars"][qc_var][z]
        
        return time, data, qc_data
    
    def _random_color(self) -> str:
        """Generate a random hex color."""
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))
    
    def _rebuild_variable_panel(self):
        """Rebuild the left panel with variable controls."""
        for widget in self._var_inner_frame.winfo_children():
            widget.destroy()
        
        row = 0
        
        # Only show sources that have selected variables (not empty)
        sources_with_data = []
        for source in sorted(self._user_selections.keys()):
            # Check if this source has any non-QC variables selected
            has_variables = False
            for z, var_list in self._user_selections[source].items():
                for var in var_list:
                    if not var.endswith("_qcflag"):
                        has_variables = True
                        break
                if has_variables:
                    break
            if has_variables:
                sources_with_data.append(source)
        
        for source in sources_with_data:
            # Source header with info button - make it visually distinct
            src_frame = tk.Frame(self._var_inner_frame, relief="ridge", borderwidth=1, bg="#f0f0f0")
            src_frame.grid(row=row, column=0, columnspan=5 + self._num_panels, sticky="ew", pady=(10, 2), padx=(0, 5))
            
            src_label = tk.Label(
                src_frame, 
                text=f"{source.upper()} ", 
                font=("Arial", 10, "bold"),
                anchor="w",
                bg="#f0f0f0"
            )
            src_label.pack(side=tk.LEFT)
            
            # Source info button
            src_info_btn = tk.Button(
                src_frame,
                text="?",
                width=2,
                font=("Arial", 7),
                command=lambda s=source: self._show_source_info(s),
                bg="#e0e0e0"
            )
            src_info_btn.pack(side=tk.LEFT, padx=5)
            
            row += 1
            
            z_vars = self._user_selections[source]
            
            all_vars = sorted(set(
                v for var_list in z_vars.values() 
                for v in var_list 
                if not v.endswith("_qcflag")
            ))
            
            for var in all_vars:
                # Variable header with info button
                var_frame = tk.Frame(self._var_inner_frame)
                var_frame.grid(row=row, column=0, columnspan=5 + self._num_panels, sticky="w", pady=(5, 1))
                
                var_label = tk.Label(
                    var_frame,
                    text=f"{var} ",
                    font=("Arial", 9, "bold"),
                    anchor="w"
                )
                var_label.pack(side=tk.LEFT)
                
                # Variable info button
                var_info_btn = tk.Button(
                    var_frame,
                    text="?",
                    width=2,
                    font=("Arial", 7),
                    command=lambda s=source, v=var: self._show_variable_info(s, v)
                )
                var_info_btn.pack(side=tk.LEFT, padx=5)
                
                row += 1
                
                # Column headers
                tk.Label(self._var_inner_frame, text="Height", width=6, anchor="w").grid(
                    row=row, column=0, sticky="w", padx=(20, 2)
                )
                tk.Label(self._var_inner_frame, text="QC", width=2).grid(row=row, column=1)
                tk.Label(self._var_inner_frame, text="", width=2).grid(row=row, column=2)
                
                # Dynamic panel headers
                for p_idx in range(self._num_panels):
                    tk.Label(self._var_inner_frame, text=f"{p_idx+1}", width=2).grid(
                        row=row, column=3 + p_idx
                    )
                row += 1
                
                heights_with_var = sorted([z for z, vlist in z_vars.items() if var in vlist])
                
                for z in heights_with_var:
                    key = (source, z, var)
                    config = self._plot_config.get(key, {
                        "color": self._random_color(), 
                        "panels": [False] * self._num_panels
                    })
                    
                    tk.Label(self._var_inner_frame, text=str(z), width=6, anchor="w").grid(
                        row=row, column=0, sticky="w", padx=(20, 2)
                    )
                    
                    # QC apply checkbox
                    if key not in self._qc_apply_vars:
                        self._qc_apply_vars[key] = tk.BooleanVar(value=True)
                    qc_cb = tk.Checkbutton(
                        self._var_inner_frame,
                        variable=self._qc_apply_vars[key]
                    )
                    qc_cb.grid(row=row, column=1)
                    
                    # Color button
                    color_btn = tk.Button(
                        self._var_inner_frame,
                        bg=config["color"],
                        width=1,
                        height=1,
                        command=lambda k=key: self._pick_color(k)
                    )
                    color_btn.grid(row=row, column=2, padx=1)
                    self._plot_config[key]["color_btn"] = color_btn
                    
                    # Panel checkboxes
                    for p_idx in range(self._num_panels):
                        var_bool = tk.BooleanVar(value=config["panels"][p_idx])
                        cb = tk.Checkbutton(
                            self._var_inner_frame,
                            variable=var_bool,
                            command=lambda k=key, idx=p_idx, v=var_bool: self._toggle_panel(k, idx, v)
                        )
                        cb.grid(row=row, column=3 + p_idx)
                        self._plot_config[key][f"panel_var_{p_idx}"] = var_bool
                    
                    row += 1
    
    def _show_source_info(self, source: str):
        """Show a popup with source/dataset attributes."""
        # Find which dataset contains this source
        attrs = {}
        for ds_name, ds in self._manager.datasets.items():
            if "source" in ds.dims:
                if source in ds["source"].values:
                    attrs = dict(ds.attrs)
                    attrs["_dataset_name"] = ds_name
                    break
            else:
                ds_source = ds.attrs.get("source", ds_name)
                if ds_source == source:
                    attrs = dict(ds.attrs)
                    attrs["_dataset_name"] = ds_name
                    break
        
        self._show_info_popup(f"Source: {source}", attrs)
    
    def _show_variable_info(self, source: str, var: str):
        """Show a popup with variable attributes."""
        attrs = {}
        for ds_name, ds in self._manager.datasets.items():
            # Check if this dataset has this source
            has_source = False
            if "source" in ds.dims:
                has_source = source in ds["source"].values
            else:
                has_source = ds.attrs.get("source", ds_name) == source
            
            if has_source and var in ds.data_vars:
                attrs = dict(ds[var].attrs)
                attrs["_dtype"] = str(ds[var].dtype)
                attrs["_dims"] = str(ds[var].dims)
                attrs["_shape"] = str(ds[var].shape)
                break
        
        self._show_info_popup(f"Variable: {var}", attrs)
    
    def _show_info_popup(self, title: str, attrs: dict):
        """Display a popup window with attribute information."""
        popup = tk.Toplevel(self)
        popup.title(title)
        popup.geometry("400x300")
        popup.transient(self)
        
        # Create scrollable text area
        text_frame = tk.Frame(popup)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, font=("Consolas", 9))
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text.yview)
        
        # Format attributes
        if attrs:
            for key, value in sorted(attrs.items()):
                text.insert(tk.END, f"{key}:\n", "key")
                text.insert(tk.END, f"  {value}\n\n")
        else:
            text.insert(tk.END, "No attributes available.")
        
        text.tag_configure("key", font=("Consolas", 9, "bold"))
        text.config(state=tk.DISABLED)
        
        # Close button
        tk.Button(popup, text="Close", command=popup.destroy, width=10).pack(pady=10)
        
        # Center on parent
        popup.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - popup.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - popup.winfo_height()) // 2
        popup.geometry(f"+{x}+{y}")
    
    def _pick_color(self, key):
        """Open color picker for a variable-height combination."""
        current_color = self._plot_config[key]["color"]
        color = colorchooser.askcolor(color=current_color, title="Pick a color")
        if color[1]:
            self._plot_config[key]["color"] = color[1]
            if "color_btn" in self._plot_config[key]:
                self._plot_config[key]["color_btn"].config(bg=color[1])
            self._update_line_color(key, color[1])
    
    def _update_line_color(self, key, new_color):
        """Update only the color of existing lines without full redraw."""
        source, z, var = key
        for p_idx in range(3):
            line_key = (source, z, var, p_idx)
            if line_key in self._plot_lines:
                artists = self._plot_lines[line_key]
                if artists[0] is not None:
                    artists[0].set_color(new_color)
        self.canvas.draw_idle()
    
    def _toggle_panel(self, key, panel_idx, var_bool):
        """Update panel assignment for a variable-height combination."""
        self._plot_config[key]["panels"][panel_idx] = var_bool.get()
        self._update_single_line(key, panel_idx, var_bool.get())
    
    def _update_single_line(self, key, panel_idx, is_active):
        """Add or remove a single line instead of redrawing everything."""
        source, z, var = key
        line_key = (source, z, var, panel_idx)
        
        # Save current x-limits before any changes
        current_xlim = self.axes[0].get_xlim()
        has_existing_data = bool(self._plot_lines)
        
        if not is_active:
            if line_key in self._plot_lines:
                for artist in self._plot_lines[line_key]:
                    if artist is not None:
                        artist.remove()
                del self._plot_lines[line_key]
            self.canvas.draw_idle()
            return
        
        cached = self._get_cached_data(source, z, var)
        if cached is None:
            print(f"No cached data for {source}/{z}/{var}")
            return
        
        time, data, qc_data = cached
        color = self._plot_config[key]["color"]
        ax = self.axes[panel_idx]
        
        line, = ax.plot(time, data, color=color, linewidth=1.0, label=f"{var} z={z}")
        
        # Create QC markers
        scatters = []
        if qc_data is not None:
            scatters = self._create_qc_scatters(ax, time, data, qc_data)
        
        self._plot_lines[line_key] = [line] + scatters
        
        # Only autoscale if not locked
        if not self._y_lock_vars[panel_idx].get():
            ax.relim()
            ax.autoscale_view()
        else:
            # Apply locked limits
            try:
                ymin = float(self._y_min_vars[panel_idx].get())
                ymax = float(self._y_max_vars[panel_idx].get())
                ax.set_ylim(ymin, ymax)
            except ValueError:
                pass
        
        # Only set x-limits to full range if this is the first plot
        # Otherwise, preserve the current view
        if not has_existing_data:
            if self._time_min_num is not None and self._time_max_num is not None:
                for a in self.axes:
                    a.set_xlim(self._time_min_num, self._time_max_num)
        else:
            # Restore the previous x-limits
            for a in self.axes:
                a.set_xlim(current_xlim)
        
        # Update time controls after plotting
        self._update_time_slider_from_axes()
        self._update_window_controls_from_axes()
        
        # Compute time bounds before formatting
        self._compute_time_bounds()
        
        # Reinitialize span selectors
        self._init_span_selectors()
        
        # Apply datetime formatting to x-axis after bounds are computed
        self._apply_datetime_formatting()
        
        self.canvas.draw_idle()
    
    def _update_plot(self):
        """Full redraw of plot - used only when necessary."""
        for ax in self.axes:
            ax.clear()
            ax.grid(True)
        
        for i, ax in enumerate(self.axes):
            ax.set_ylabel(f"Panel {i+1}")
        self.axes[2].set_xlabel("Time")
        
        # Apply datetime formatting to x-axis
        self._apply_datetime_formatting()
        
        self._plot_lines.clear()
        
        for (source, z, var), config in self._plot_config.items():
            if var.endswith("_qc_flag"):
                continue
            
            panels = config["panels"]
            if not any(panels):
                continue
            
            color = config["color"]
            cached = self._get_cached_data(source, z, var)
            
            if cached is None:
                continue
            
            time, data, qc_data = cached
            
            for p_idx, active in enumerate(panels):
                if active:
                    line, = self.axes[p_idx].plot(time, data, color=color, linewidth=1.0,
                                                   label=f"{var} z={z}")
                    
                    scatters = []
                    if qc_data is not None:
                        scatters = self._create_qc_scatters(self.axes[p_idx], time, data, qc_data)
                    
                    line_key = (source, z, var, p_idx)
                    self._plot_lines[line_key] = [line] + scatters
        
        # Apply locked y-ranges after plotting
        self._apply_locked_y_ranges()
        
        # Update time controls
        self._update_time_slider_from_axes()
        self._update_window_controls_from_axes()
        
        # Compute time bounds before formatting
        self._compute_time_bounds()
        
        # Reinitialize span selectors
        self._init_span_selectors()
        
        # Apply datetime formatting to x-axis after bounds are computed
        self._apply_datetime_formatting()
        
        self.canvas.draw_idle()
    
    @property
    def manager(self) -> DatasetManager:
        """Access the underlying DatasetManager."""
        return self._manager
    
    @property
    def selections(self) -> dict:
        """Get the current user selections."""
        return self._user_selections
    
def run_app():
    """Run the application standalone."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Graphical User Interface for timer series plot and quality control of NetCDF datasets.")
    parser.add_argument(
        "-n", "--num-panels",
        type=int,
        default=None,
        help="Number of plot panels to display (overrides settings.yaml)"
    )
    parser.add_argument(
        "-m", "--minsize",
        type=int,
        default=None,
        help="Minimum size of left panel (overrides settings.yaml)"
    )
    parser.add_argument(
        "-w", "--width",
        type=int,
        default=None,
        help="Width of left panel (overrides settings.yaml)"
    )
    
    args = parser.parse_args()
    
    root = tk.Tk()
    root.title("WindCDF - The NetCDF app for data quality control")
    root.geometry("1400x800")
    
    app = WindCDF_GUI(master=root, num_panels=args.num_panels, minsize=args.minsize, width=args.width)
    app.mainloop()


if __name__ == "__main__":
    run_app()