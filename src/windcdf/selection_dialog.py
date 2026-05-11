import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any


class SelectionDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        height_vars: dict,
        qc_map: dict,
        on_confirm,
        show_clip_option: bool = False,
        current_dataset_name: str = "",
        existing_dataset_names: set[str] | None = None,
    ):
        super().__init__(parent)
        self._height_vars = height_vars
        self._qc_map = qc_map
        self._on_confirm = on_confirm
        self._show_clip_option = show_clip_option
        self._current_dataset_name = current_dataset_name
        self._existing_dataset_names = existing_dataset_names or set()
        self._dataset_name_var = tk.StringVar(value=current_dataset_name)
        self._checkbox_vars: dict[str, dict[Any, tk.BooleanVar]] = {}
        self._clip_var: tk.BooleanVar = tk.BooleanVar(value=True)

        self._var_master_checkboxes: dict[str, tk.BooleanVar] = {}
        self._height_master_checkboxes: dict[Any, tk.BooleanVar] = {}

        self._construct_dialog()

    def _construct_dialog(self):
        """Build dialog components."""
        name_frame = tk.Frame(self)
        name_frame.pack(fill="x", padx=10, pady=(10, 5))

        tk.Label(
            name_frame,
            text="Dataset name:",
            font=("Arial", 10, "bold")
        ).pack(side="left")

        tk.Entry(
            name_frame,
            textvariable=self._dataset_name_var,
            width=40
        ).pack(side="left", padx=(8, 0))

        if self._show_clip_option:
            clip_frame = tk.Frame(self)
            clip_frame.pack(fill="x", padx=10, pady=(10, 5))

            tk.Label(
                clip_frame,
                text=f"Dataset: {self._current_dataset_name}",
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

        all_heights = sorted(self._height_vars.keys())
        all_vars = sorted(set(var for var_list in self._height_vars.values() for var in var_list))

        if not all_heights or not all_vars:
            tk.Label(inner_frame, text="No valid variables found in dataset.").pack(padx=10, pady=10)
        else:
            tk.Label(inner_frame, text="Variable \\ Height", relief="ridge", width=18).grid(
                row=0, column=0, sticky="nsew"
            )
            tk.Label(inner_frame, text="All", relief="ridge", width=4).grid(
                row=0, column=1, sticky="nsew"
            )

            for col_idx, height in enumerate(all_heights, start=2):
                height_master_var = tk.BooleanVar(value=True)
                self._height_master_checkboxes[height] = height_master_var

                height_frame = tk.Frame(inner_frame, relief="ridge", borderwidth=1)
                height_frame.grid(row=0, column=col_idx, sticky="nsew")

                tk.Label(height_frame, text=str(height), width=8).pack()
                tk.Checkbutton(
                    height_frame,
                    variable=height_master_var,
                    command=lambda ht=height: self._toggle_height(ht)
                ).pack()

            row = 1
            for var in all_vars:
                tk.Label(inner_frame, text=var, relief="ridge", width=18, anchor="w").grid(
                    row=row, column=0, sticky="nsew"
                )

                var_master_var = tk.BooleanVar(value=True)
                self._var_master_checkboxes[var] = var_master_var
                tk.Checkbutton(
                    inner_frame,
                    variable=var_master_var,
                    command=lambda v=var: self._toggle_variable(v)
                ).grid(row=row, column=1, sticky="nsew")

                self._checkbox_vars[var] = {}

                for col_idx, height in enumerate(all_heights, start=2):
                    is_valid = var in self._height_vars.get(height, [])

                    if is_valid:
                        bool_var = tk.BooleanVar(value=True)
                        self._checkbox_vars[var][height] = bool_var
                        cb = tk.Checkbutton(
                            inner_frame,
                            variable=bool_var,
                            command=self._update_master_checkboxes
                        )
                        cb.grid(row=row, column=col_idx, sticky="nsew")
                    else:
                        tk.Label(inner_frame, text="-", relief="flat").grid(
                            row=row, column=col_idx, sticky="nsew"
                        )

                row += 1

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)

        tk.Button(btn_frame, text="Confirm Selection", command=self._confirm_selection).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

    def _select_all(self):
        """Select all checkboxes."""
        for var in self._checkbox_vars:
            for height in self._checkbox_vars[var]:
                self._checkbox_vars[var][height].set(True)

        for var in self._var_master_checkboxes:
            self._var_master_checkboxes[var].set(True)

        for height in self._height_master_checkboxes:
            self._height_master_checkboxes[height].set(True)

    def _unselect_all(self):
        """Unselect all checkboxes."""
        for var in self._checkbox_vars:
            for height in self._checkbox_vars[var]:
                self._checkbox_vars[var][height].set(False)

        for var in self._var_master_checkboxes:
            self._var_master_checkboxes[var].set(False)

        for height in self._height_master_checkboxes:
            self._height_master_checkboxes[height].set(False)

    def _toggle_variable(self, var: str):
        """Toggle all heights for a specific variable."""
        new_state = self._var_master_checkboxes[var].get()

        for height in self._checkbox_vars[var]:
            self._checkbox_vars[var][height].set(new_state)

        self._update_master_checkboxes()

    def _toggle_height(self, height):
        """Toggle all variables for a specific height."""
        new_state = self._height_master_checkboxes[height].get()

        for var in self._checkbox_vars:
            if height in self._checkbox_vars[var]:
                self._checkbox_vars[var][height].set(new_state)

        self._update_master_checkboxes()

    def _update_master_checkboxes(self):
        """Update master checkboxes based on individual checkbox states."""
        for var in self._var_master_checkboxes:
            if var in self._checkbox_vars:
                states = [cb.get() for cb in self._checkbox_vars[var].values()]
                if states:
                    self._var_master_checkboxes[var].set(all(states))

        for height in self._height_master_checkboxes:
            states = []
            for var in self._checkbox_vars:
                if height in self._checkbox_vars[var]:
                    states.append(self._checkbox_vars[var][height].get())
            if states:
                self._height_master_checkboxes[height].set(all(states))

    def _confirm_selection(self):
        """Gather selections and invoke callback."""
        final_selection = {}

        for var, height_bools in self._checkbox_vars.items():
            for height, bool_var in height_bools.items():
                if bool_var.get():
                    if height not in final_selection:
                        final_selection[height] = []

                    final_selection[height].append(var)

                    if self._qc_map.get(var):
                        qc_var = f"{var}_qcflag"
                        if qc_var not in final_selection[height]:
                            final_selection[height].append(qc_var)

        dataset_name = self._dataset_name_var.get().strip()
        if not dataset_name:
            messagebox.showerror("Invalid Name", "Please enter a dataset name.")
            return

        if dataset_name in self._existing_dataset_names and dataset_name != self._current_dataset_name:
            messagebox.showerror("Duplicate Name", f"Dataset '{dataset_name}' already exists.")
            return

        clip_to_range = self._clip_var.get() if self._show_clip_option else False
        self._on_confirm(final_selection, clip_to_range, dataset_name)
        self.destroy()