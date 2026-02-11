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
            src_label.grid(row=current_row, column=0, sticky="w", pady=(15, 5))
            current_row += 1
            
            all_heights = sorted(z_vars.keys())
            all_vars = sorted(set(v for var_list in z_vars.values() for v in var_list))
            
            if not all_vars or not all_heights:
                continue
            
            self._checkbox_vars[source] = {}
            
            tk.Label(inner_frame, text="Variable \\ Height", relief="ridge", width=18).grid(
                row=current_row, column=0, sticky="nsew"
            )
            for col_idx, h in enumerate(all_heights, start=1):
                tk.Label(inner_frame, text=str(h), relief="ridge", width=8).grid(
                    row=current_row, column=col_idx, sticky="nsew"
                )
            current_row += 1
            
            for var in all_vars:
                tk.Label(inner_frame, text=var, relief="ridge", width=18, anchor="w").grid(
                    row=current_row, column=0, sticky="nsew"
                )
                
                self._checkbox_vars[source][var] = {}
                
                for col_idx, h in enumerate(all_heights, start=1):
                    is_valid = var in z_vars.get(h, [])
                    
                    if is_valid:
                        bool_var = tk.BooleanVar(value=True)  # Default to selected
                        self._checkbox_vars[source][var][h] = bool_var
                        cb = tk.Checkbutton(inner_frame, variable=bool_var)
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