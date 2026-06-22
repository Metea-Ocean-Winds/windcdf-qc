import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Callable


class SelectionDialog(tk.Toplevel):
    def __init__(
        self,
        parent,
        selection_map: dict,
        qc_map: dict,
        on_confirm,
        selector_labeler: Callable[[Any], str],
        selector_sort_key: Callable[[Any], Any],
        dimension_names: list[str] | None = None,
        show_clip_option: bool = False,
        current_dataset_name: str = "",
        existing_dataset_names: set[str] | None = None,
    ):
        super().__init__(parent)
        self._selection_map = selection_map
        self._qc_map = qc_map
        self._on_confirm = on_confirm
        self._selector_labeler = selector_labeler
        self._selector_sort_key = selector_sort_key
        self._dimension_names = dimension_names or []
        self._show_clip_option = show_clip_option
        self._current_dataset_name = current_dataset_name
        self._existing_dataset_names = existing_dataset_names or set()
        self._dataset_name_var = tk.StringVar(value=current_dataset_name)
        self._checkbox_vars: dict[str, dict[Any, tk.BooleanVar]] = {}
        self._clip_var: tk.BooleanVar = tk.BooleanVar(value=True)

        self._var_master_checkboxes: dict[str, tk.BooleanVar] = {}
        self._selector_master_checkboxes: dict[Any, tk.BooleanVar] = {}

        self._construct_dialog()

    def _construct_dialog(self):
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

        all_selectors = sorted(self._selection_map.keys(), key=self._selector_sort_key)
        all_vars = sorted(set(var for var_list in self._selection_map.values() for var in var_list))

        selector_title = " / ".join(self._dimension_names) if self._dimension_names else "Selection"

        if not all_selectors or not all_vars:
            tk.Label(inner_frame, text="No valid variables found in dataset.").pack(padx=10, pady=10)
        else:
            tk.Label(inner_frame, text=f"Variable \\ {selector_title}", relief="ridge", width=24).grid(
                row=0, column=0, sticky="nsew"
            )
            tk.Label(inner_frame, text="All", relief="ridge", width=4).grid(
                row=0, column=1, sticky="nsew"
            )

            for col_idx, selector_key in enumerate(all_selectors, start=2):
                selector_master_var = tk.BooleanVar(value=True)
                self._selector_master_checkboxes[selector_key] = selector_master_var

                selector_frame = tk.Frame(inner_frame, relief="ridge", borderwidth=1)
                selector_frame.grid(row=0, column=col_idx, sticky="nsew")

                tk.Label(
                    selector_frame,
                    text=self._selector_labeler(selector_key),
                    width=18,
                    wraplength=140,
                    justify="center"
                ).pack()

                tk.Checkbutton(
                    selector_frame,
                    variable=selector_master_var,
                    command=lambda sel=selector_key: self._toggle_selector(sel)
                ).pack()

            row = 1
            for var in all_vars:
                tk.Label(inner_frame, text=var, relief="ridge", width=24, anchor="w").grid(
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

                for col_idx, selector_key in enumerate(all_selectors, start=2):
                    is_valid = var in self._selection_map.get(selector_key, [])

                    if is_valid:
                        bool_var = tk.BooleanVar(value=True)
                        self._checkbox_vars[var][selector_key] = bool_var
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
        for var in self._checkbox_vars:
            for selector_key in self._checkbox_vars[var]:
                self._checkbox_vars[var][selector_key].set(True)

        for var in self._var_master_checkboxes:
            self._var_master_checkboxes[var].set(True)

        for selector_key in self._selector_master_checkboxes:
            self._selector_master_checkboxes[selector_key].set(True)

    def _unselect_all(self):
        for var in self._checkbox_vars:
            for selector_key in self._checkbox_vars[var]:
                self._checkbox_vars[var][selector_key].set(False)

        for var in self._var_master_checkboxes:
            self._var_master_checkboxes[var].set(False)

        for selector_key in self._selector_master_checkboxes:
            self._selector_master_checkboxes[selector_key].set(False)

    def _toggle_variable(self, var: str):
        new_state = self._var_master_checkboxes[var].get()

        for selector_key in self._checkbox_vars[var]:
            self._checkbox_vars[var][selector_key].set(new_state)

        self._update_master_checkboxes()

    def _toggle_selector(self, selector_key):
        new_state = self._selector_master_checkboxes[selector_key].get()

        for var in self._checkbox_vars:
            if selector_key in self._checkbox_vars[var]:
                self._checkbox_vars[var][selector_key].set(new_state)

        self._update_master_checkboxes()

    def _update_master_checkboxes(self):
        for var in self._var_master_checkboxes:
            if var in self._checkbox_vars:
                states = [cb.get() for cb in self._checkbox_vars[var].values()]
                if states:
                    self._var_master_checkboxes[var].set(all(states))

        for selector_key in self._selector_master_checkboxes:
            states = []
            for var in self._checkbox_vars:
                if selector_key in self._checkbox_vars[var]:
                    states.append(self._checkbox_vars[var][selector_key].get())
            if states:
                self._selector_master_checkboxes[selector_key].set(all(states))

    def _confirm_selection(self):
        final_selection = {}

        for var, selector_bools in self._checkbox_vars.items():
            for selector_key, bool_var in selector_bools.items():
                if bool_var.get():
                    final_selection.setdefault(selector_key, []).append(var)

                    if self._qc_map.get(var):
                        qc_var = f"{var}_qcflag"
                        if qc_var not in final_selection[selector_key]:
                            final_selection[selector_key].append(qc_var)

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