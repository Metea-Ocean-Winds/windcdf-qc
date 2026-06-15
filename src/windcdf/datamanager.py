import itertools
from typing import Any

import pandas as pd
import xarray as xr


class DatasetManager:
    """Manages xr.Datasets with time range clipping and selection metadata.

    The first added dataset sets the reference time range.
    Subsequent datasets can be clipped to this time range.

    Dataset dimension rules:
    - time only -> single series per variable
    - time + N extra dims -> one selectable 1D time series per combination
      of non-time dimensions used by each variable
    """

    def __init__(self, time_dim: str = "time"):
        self.time_dim = time_dim
        self.datasets: dict[str, xr.Dataset] = {}
        self.time_range: tuple | None = None
        self._nested_dicts: dict[str, dict] = {}
        self._dataset_info: dict[str, dict] = {}

    def _get_extra_dims(self, ds: xr.Dataset) -> list[str]:
        return [dim for dim in ds.dims if dim != self.time_dim]

    def _get_var_extra_dims(self, da: xr.DataArray) -> list[str]:
        return [dim for dim in da.dims if dim != self.time_dim]

    def _validate_dataset(self, ds: xr.Dataset, name: str) -> dict:
        if self.time_dim not in ds.dims:
            raise ValueError(f"Dataset '{name}' is missing required '{self.time_dim}' dimension")

        if ds[self.time_dim].ndim != 1:
            raise ValueError(f"Dataset '{name}': time dimension must be 1D")

        extra_dims = self._get_extra_dims(ds)
        return {
            "extra_dims": extra_dims,
            "shape_type": "time_only" if not extra_dims else "time_plus_n",
        }

    def _is_valid_variable(self, var_name: str, da: xr.DataArray) -> bool:
        if var_name.endswith("_qcflag"):
            return False
        if self.time_dim not in da.dims:
            return False
        if da.isnull().all():
            return False
        return True

    def add_dataset(
        self,
        name: str,
        ds: xr.Dataset,
        set_time_range: bool = False,
    ) -> None:
        ds_info = self._validate_dataset(ds, name)

        if not self.datasets or set_time_range:
            self._set_time_range(ds)

        self.datasets[name] = ds
        self._dataset_info[name] = ds_info
        self._nested_dicts[name] = self._generate_nested_dict(ds, ds_info)

    def rename_dataset(self, old_name: str, new_name: str) -> None:
        if old_name not in self.datasets:
            raise KeyError(f"Dataset '{old_name}' not found.")
        if new_name != old_name and new_name in self.datasets:
            raise ValueError(f"Dataset '{new_name}' already exists.")

        self.datasets[new_name] = self.datasets.pop(old_name)
        self._nested_dicts[new_name] = self._nested_dicts.pop(old_name)
        self._dataset_info[new_name] = self._dataset_info.pop(old_name)

    def _set_time_range(self, ds: xr.Dataset) -> None:
        first_time = ds[self.time_dim].values[0]
        last_time = ds[self.time_dim].values[-1]
        self.time_range = (first_time, last_time)

    def get_time_range(self, as_pandas: bool = True) -> tuple:
        if self.time_range is None:
            raise ValueError("No time range set. Add a dataset first.")

        first_time, last_time = self.time_range
        if as_pandas:
            first_time = pd.Timestamp(first_time)
            last_time = pd.Timestamp(last_time)

        return first_time, last_time

    def clip_to_time_range(self, name: str) -> xr.Dataset:
        if self.time_range is None:
            raise ValueError("No time range set. Add a dataset first.")

        if name not in self.datasets:
            raise KeyError(f"Dataset '{name}' not found.")

        first_time, last_time = self.time_range
        return self.datasets[name].sel({self.time_dim: slice(first_time, last_time)})

    @staticmethod
    def _to_python_type(val):
        if hasattr(val, "item"):
            return val.item()
        return val

    def _make_selector_key(
        self,
        dims: list[str],
        values: tuple[Any, ...]
    ) -> tuple[tuple[str, Any], ...]:
        return tuple(
            (dim, self._to_python_type(value))
            for dim, value in zip(dims, values)
        )

    def selector_key_to_indexers(
        self,
        selector_key: tuple[tuple[str, Any], ...] | None
    ) -> dict[str, Any]:
        if not selector_key:
            return {}
        return {dim: value for dim, value in selector_key}

    def format_selector_label(
        self,
        selector_key: tuple[tuple[str, Any], ...] | None
    ) -> str:
        if not selector_key:
            return "all"
        return " | ".join(f"{dim}={value}" for dim, value in selector_key)
    
    def selector_sort_key(
        self,
        selector_key: tuple[tuple[str, Any], ...] | None
    ):
        """Sort selectors by dimension name first, then numeric values ascending within each dimension."""
        if not selector_key:
            return (("", 0, 0.0),)

        sort_parts = []

        for dim, value in selector_key:
            dim_key = str(dim).lower()

            try:
                numeric_value = float(value)
                sort_parts.append((dim_key, 0, numeric_value))
            except (TypeError, ValueError):
                sort_parts.append((dim_key, 1, str(value).lower()))

        return tuple(sort_parts)

    def iter_var_selectors(
        self,
        ds: xr.Dataset,
        var_name: str,
    ):
        da = ds[var_name]
        extra_dims = self._get_var_extra_dims(da)

        if not extra_dims:
            yield tuple(), {}
            return

        coord_lists = [
            [self._to_python_type(v) for v in ds[dim].values]
            for dim in extra_dims
        ]

        for values in itertools.product(*coord_lists):
            indexers = dict(zip(extra_dims, values))
            yield self._make_selector_key(extra_dims, values), indexers

    def _generate_nested_dict(self, ds: xr.Dataset, ds_info: dict) -> dict:
        """Generate selector_key -> [variables] mapping for the selection dialog."""
        nested_dict: dict = {}

        valid_vars = [
            var for var in ds.data_vars
            if self._is_valid_variable(var, ds[var])
        ]

        if not valid_vars:
            return nested_dict

        for var in valid_vars:
            da = ds[var]

            for selector_key, indexers in self.iter_var_selectors(ds, var):
                sliced = da if not indexers else da.sel(indexers)
                if sliced.isnull().all():
                    continue

                nested_dict.setdefault(selector_key, []).append(var)

        return {
            selector_key: sorted(set(var_list))
            for selector_key, var_list in nested_dict.items()
        }

    def get_nested_dict(self, name: str) -> dict:
        if name not in self._nested_dicts:
            raise KeyError(f"Dataset '{name}' not found.")
        return self._nested_dicts[name]

    def get_all_nested_dicts(self) -> dict:
        return self._nested_dicts

    def get_dataset_info(self, name: str) -> dict:
        if name not in self._dataset_info:
            raise KeyError(f"Dataset '{name}' not found.")
        return self._dataset_info[name]

    def get_series_data(
        self,
        dataset_name: str,
        var_name: str,
        selector_key: tuple[tuple[str, Any], ...] | None = None
    ) -> xr.DataArray:
        if dataset_name not in self.datasets:
            raise KeyError(f"Dataset '{dataset_name}' not found.")

        ds = self.datasets[dataset_name]
        da = ds[var_name]
        indexers = self.selector_key_to_indexers(selector_key)
        valid_indexers = {
            dim: value for dim, value in indexers.items()
            if dim in da.dims
        }

        if not valid_indexers:
            return da

        return da.sel(valid_indexers)

    def get_vars_with_qc_flags(self, name: str) -> dict[str, bool]:
        if name not in self.datasets:
            raise KeyError(f"Dataset '{name}' not found.")

        ds = self.datasets[name]
        all_vars = list(ds.data_vars)
        qc_flags = {var for var in all_vars if var.endswith("_qcflag")}

        base_vars_with_qc = [
            var for var in all_vars
            if not var.endswith("_qcflag")
            and f"{var}_qcflag" in qc_flags
            and self._is_valid_variable(var, ds[var])
        ]

        return {var_name: True for var_name in base_vars_with_qc}

    def get_all_vars_with_qc_flags(self) -> dict[str, dict[str, bool]]:
        return {name: self.get_vars_with_qc_flags(name) for name in self.datasets}

    def __repr__(self) -> str:
        datasets_info = ", ".join(self.datasets.keys()) if self.datasets else "None"
        time_info = f"{self.time_range}" if self.time_range else "Not set"
        return f"DatasetManager(datasets=[{datasets_info}], time_range={time_info})"