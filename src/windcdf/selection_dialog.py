import tkinter as tk
from tkinter import ttk


class SelectionDialog(tk.Toplevel):
    """Dialog for selecting variables at different heights per source."""
    
    def __init__(self, parent, source_z_vars: dict, qc_map: dict, on_confirm, 
                 show_clip_option: bool = False, dataset_name: str = ""):
        super().__init__(parent)
        self.title("Variable & Height Selection")
        self.geometry("850x650")
        self.transient(parent)
        self.grab_set()
        
        self._source_z_vars = source_z_vars
        self._qc_map = qc_map
        self._on_confirm = on_confirm
        self._show_clip_option = show_clip_option
        self._dataset_name = dataset_name
        self._checkbox_vars: dict[str, dict[str, dict[str, tk.BooleanVar]]] = {}
        self._clip_var: tk.BooleanVar = tk.BooleanVar(value=True)
        
        # Master controls for variables and heights per source
        self._var_master_checkboxes: dict[str, dict[str, tk.BooleanVar]] = {}
        self._height_master_checkboxes: dict[str, dict[str, tk.BooleanVar]] = {}
        
        self._construct_dialog()
    
    def _construct_dialog(self):
        """Build dialog components."""
        # Clip option at top (only for second+ datasets)
        if self._show_clip_option:
            clip_frame = tk.Frame(self)
            clip_frame.pack(fill="x", padx=10, pady=(10, 5))
            
            tk.Label(
                clip_frame, 
                text=f"Dataset: {self._dataset_name}", 
                font=("Arial", 10, "bold")
            ).pack(side="left", padx=(0, 10))
            
            tk.Checkbutton(
                clip_frame,
                text="Clip to reference time range",
                variable=self._clip_var,
                font=("Arial", 9)
            ).pack(side="left")
            
            tk.Label(
                clip_frame,
                text="(from first loaded dataset)",
                font=("Arial", 8),
                fg="gray"
            ).pack(side="left", padx=(5, 0))
        
        # Select All / Unselect All buttons
        btn_top_frame = tk.Frame(self)
        btn_top_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Button(
            btn_top_frame, 
            text="Select All", 
            command=self._select_all,
            font=("Arial", 9)
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_top_frame, 
            text="Unselect All", 
            command=self._unselect_all,
            font=("Arial", 9)
        ).pack(side=tk.LEFT, padx=5)
        
        container = tk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        scroll_canvas = tk.Canvas(container)
        v_scrollbar = ttk.Scrollbar(container, orient="vertical", command=scroll_canvas.yview)
        h_scrollbar = ttk.Scrollbar(container, orient="horizontal", command=scroll_canvas.xview)
        
        inner_frame = tk.Frame(scroll_canvas)
        inner_frame.bind("<Configure>", lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        
        scroll_canvas.create_window((0, 0), window=inner_frame, anchor="nw")
        scroll_canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        scroll_canvas.pack(side="left", fill="both", expand=True)
        
        current_row = 0
        for source, z_vars in self._source_z_vars.items():
            if not z_vars:
                continue
            
            src_label = tk.Label(inner_frame, text=f"Source: {source}", font=("Arial", 11, "bold"))
            src_label.grid(row=current_row, column=0, sticky="w", pady=(15, 5), columnspan=2)
            current_row += 1
            
            all_heights = sorted(z_vars.keys())
            all_vars = sorted(set(v for var_list in z_vars.values() for v in var_list))
            
            if not all_vars or not all_heights:
                continue
            
            self._checkbox_vars[source] = {}
            self._var_master_checkboxes[source] = {}
            self._height_master_checkboxes[source] = {}
            
            # Header row with master height checkboxes
            tk.Label(inner_frame, text="Variable \\ Height", relief="ridge", width=18).grid(
                row=current_row, column=0, sticky="nsew"
            )
            tk.Label(inner_frame, text="All", relief="ridge", width=4).grid(
                row=current_row, column=1, sticky="nsew"
            )
            
            for col_idx, h in enumerate(all_heights, start=2):
                # Create master checkbox for this height
                height_master_var = tk.BooleanVar(value=True)
                self._height_master_checkboxes[source][h] = height_master_var
                
                # Frame to hold label and checkbox
                height_frame = tk.Frame(inner_frame, relief="ridge", borderwidth=1)
                height_frame.grid(row=current_row, column=col_idx, sticky="nsew")
                
                tk.Label(height_frame, text=str(h), width=8).pack()
                tk.Checkbutton(
                    height_frame, 
                    variable=height_master_var,
                    command=lambda s=source, ht=h: self._toggle_height(s, ht)
                ).pack()
            
            current_row += 1
            
            # Variable rows with master variable checkboxes
            for var in all_vars:
                tk.Label(inner_frame, text=var, relief="ridge", width=18, anchor="w").grid(
                    row=current_row, column=0, sticky="nsew"
                )
                
                # Master checkbox for this variable
                var_master_var = tk.BooleanVar(value=True)
                self._var_master_checkboxes[source][var] = var_master_var
                tk.Checkbutton(
                    inner_frame, 
                    variable=var_master_var,
                    command=lambda s=source, v=var: self._toggle_variable(s, v)
                ).grid(row=current_row, column=1, sticky="nsew")
                
                self._checkbox_vars[source][var] = {}
                
                for col_idx, h in enumerate(all_heights, start=2):
                    is_valid = var in z_vars.get(h, [])
                    
                    if is_valid:
                        bool_var = tk.BooleanVar(value=True)  # Default to selected
                        self._checkbox_vars[source][var][h] = bool_var
                        cb = tk.Checkbutton(
                            inner_frame, 
                            variable=bool_var,
                            command=lambda s=source: self._update_master_checkboxes(s)
                        )
                        cb.grid(row=current_row, column=col_idx, sticky="nsew")
                    else:
                        tk.Label(inner_frame, text="-", relief="flat").grid(
                            row=current_row, column=col_idx, sticky="nsew"
                        )
                
                current_row += 1
        
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(btn_frame, text="Confirm Selection", command=self._confirm_selection).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)
    
    def _select_all(self):
        """Select all checkboxes."""
        for source in self._checkbox_vars:
            for var in self._checkbox_vars[source]:
                for h in self._checkbox_vars[source][var]:
                    self._checkbox_vars[source][var][h].set(True)
            
            # Update master checkboxes
            for var in self._var_master_checkboxes.get(source, {}):
                self._var_master_checkboxes[source][var].set(True)
            for h in self._height_master_checkboxes.get(source, {}):
                self._height_master_checkboxes[source][h].set(True)
    
    def _unselect_all(self):
        """Unselect all checkboxes."""
        for source in self._checkbox_vars:
            for var in self._checkbox_vars[source]:
                for h in self._checkbox_vars[source][var]:
                    self._checkbox_vars[source][var][h].set(False)
            
            # Update master checkboxes
            for var in self._var_master_checkboxes.get(source, {}):
                self._var_master_checkboxes[source][var].set(False)
            for h in self._height_master_checkboxes.get(source, {}):
                self._height_master_checkboxes[source][h].set(False)
    
    def _toggle_variable(self, source: str, var: str):
        """Toggle all heights for a specific variable."""
        new_state = self._var_master_checkboxes[source][var].get()
        
        for h in self._checkbox_vars[source][var]:
            self._checkbox_vars[source][var][h].set(new_state)
        
        # Update height master checkboxes
        self._update_master_checkboxes(source)
    
    def _toggle_height(self, source: str, height):
        """Toggle all variables for a specific height."""
        new_state = self._height_master_checkboxes[source][height].get()
        
        for var in self._checkbox_vars[source]:
            if height in self._checkbox_vars[source][var]:
                self._checkbox_vars[source][var][height].set(new_state)
        
        # Update variable master checkboxes
        self._update_master_checkboxes(source)
    
    def _update_master_checkboxes(self, source: str):
        """Update master checkboxes based on individual checkbox states."""
        # Update variable master checkboxes
        for var in self._var_master_checkboxes.get(source, {}):
            if var in self._checkbox_vars[source]:
                states = [cb.get() for cb in self._checkbox_vars[source][var].values()]
                if states:
                    # Set to True only if all are True
                    self._var_master_checkboxes[source][var].set(all(states))
        
        # Update height master checkboxes
        for h in self._height_master_checkboxes.get(source, {}):
            states = []
            for var in self._checkbox_vars[source]:
                if h in self._checkbox_vars[source][var]:
                    states.append(self._checkbox_vars[source][var][h].get())
            if states:
                # Set to True only if all are True
                self._height_master_checkboxes[source][h].set(all(states))
    
    def _confirm_selection(self):
        """Gather selections and invoke callback."""
        final_selection = {}
        
        for source, var_heights in self._checkbox_vars.items():
            final_selection[source] = {}
            
            for var, height_bools in var_heights.items():
                for h, bool_var in height_bools.items():
                    if bool_var.get():
                        if h not in final_selection[source]:
                            final_selection[source][h] = []
                        
                        final_selection[source][h].append(var)
                        
                        if self._qc_map.get(source, {}).get(var):
                            qc_var = f"{var}_qcflag"
                            if qc_var not in final_selection[source][h]:
                                final_selection[source][h].append(qc_var)
        
        # Include clip option in callback
        clip_to_range = self._clip_var.get() if self._show_clip_option else False
        self._on_confirm(final_selection, clip_to_range)
        self.destroy()