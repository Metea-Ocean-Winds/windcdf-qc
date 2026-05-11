import xarray as xr
import pandas as pd


class DatasetManager:
    """Manages xr.Datasets with time range clipping and selection metadata.

    The first added dataset sets the reference time range.
    Subsequent datasets can be clipped to this time range.

    Dataset dimension rules:
    - `time` only -> single series per variable
    - `time + 1 extra dim` -> the extra dim is the selection axis
    - `time + more than 1 extra dim` -> reject dataset
    """

    def __init__(self, time_dim: str = "time"):
        """Initialize the DatasetManager."""
        self.time_dim = time_dim
        self.datasets: dict[str, xr.Dataset] = {}
        self.time_range: tuple | None = None
        self._nested_dicts: dict[str, dict] = {}
        self._dataset_info: dict[str, dict] = {}

    def _get_extra_dims(self, ds: xr.Dataset) -> list[str]:
        """Get extra dimensions excluding time."""
        return [dim for dim in ds.dims if dim != self.time_dim]

    def _validate_dataset(self, ds: xr.Dataset, name: str, series_dim: str | None = None) -> dict:
        """Validate dataset and classify its structure.

        Returns
        -------
        dict
            Dataset info with shape_type and series_dim.

        Raises
        ------
        ValueError
            If the dataset is missing the time dimension, time is not 1D,
            or has more than 1 extra dimension.
        """
        if self.time_dim not in ds.dims:
            raise ValueError(f"Dataset '{name}' is missing required '{self.time_dim}' dimension")

        if ds[self.time_dim].ndim != 1:
            raise ValueError(f"Dataset '{name}': time dimension must be 1D")

        extra_dims = self._get_extra_dims(ds)
        n_extra = len(extra_dims)

        if n_extra > 1:
            raise ValueError(
                f"Dataset '{name}' has {n_extra} extra dimensions {extra_dims}. "
                f"Maximum allowed is 1 (time + 1 extra dim)."
            )

        if n_extra == 0:
            return {
                "extra_dims": [],
                "series_dim": None,
                "shape_type": "time_only",
            }

        return {
            "extra_dims": extra_dims,
            "series_dim": extra_dims[0],
            "shape_type": "time_plus_1",
        }

    def _is_valid_variable(self, var_name: str, da: xr.DataArray) -> bool:
        """Check if a variable is valid for selection."""
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
        series_dim: str | None = None
    ) -> None:
        """Add a dataset to the manager."""
        ds_info = self._validate_dataset(ds, name, series_dim)

        if not self.datasets or set_time_range:
            self._set_time_range(ds)

        self.datasets[name] = ds
        self._dataset_info[name] = ds_info
        self._nested_dicts[name] = self._generate_nested_dict(ds, ds_info)

    def rename_dataset(self, old_name: str, new_name: str) -> None:
        """Rename a registered dataset."""
        if old_name not in self.datasets:
            raise KeyError(f"Dataset '{old_name}' not found.")
        if new_name != old_name and new_name in self.datasets:
            raise ValueError(f"Dataset '{new_name}' already exists.")

        self.datasets[new_name] = self.datasets.pop(old_name)
        self._nested_dicts[new_name] = self._nested_dicts.pop(old_name)
        self._dataset_info[new_name] = self._dataset_info.pop(old_name)

    def _set_time_range(self, ds: xr.Dataset) -> None:
        """Set the reference time range from a dataset."""
        first_time = ds[self.time_dim].values[0]
        last_time = ds[self.time_dim].values[-1]
        self.time_range = (first_time, last_time)

    def get_time_range(self, as_pandas: bool = True) -> tuple:
        """Return the reference time range."""
        if self.time_range is None:
            raise ValueError("No time range set. Add a dataset first.")

        first_time, last_time = self.time_range
        if as_pandas:
            first_time = pd.Timestamp(first_time)
            last_time = pd.Timestamp(last_time)

        return first_time, last_time

    def clip_to_time_range(self, name: str) -> xr.Dataset:
        """Clip a dataset to the reference time range."""
        if self.time_range is None:
            raise ValueError("No time range set. Add a dataset first.")

        if name not in self.datasets:
            raise KeyError(f"Dataset '{name}' not found.")

        first_time, last_time = self.time_range
        return self.datasets[name].sel({self.time_dim: slice(first_time, last_time)})

    def _generate_nested_dict(self, ds: xr.Dataset, ds_info: dict) -> dict:
        """Generate height/series -> [variables] mapping for the selection dialog."""
        shape_type = ds_info["shape_type"]
        nested_dict: dict = {}

        valid_vars = [
            var for var in ds.data_vars
            if self._is_valid_variable(var, ds[var])
        ]

        if not valid_vars:
            return nested_dict

        if shape_type == "time_only":
            nested_dict["all"] = valid_vars
            return nested_dict

        series_dim = ds_info["series_dim"]

        for series_val in ds[series_dim].values:
            key = self._to_python_type(series_val)
            vars_at_slice = [
                var for var in valid_vars
                if not ds[var].sel({series_dim: series_val}).isnull().all()
            ]
            if vars_at_slice:
                nested_dict[key] = vars_at_slice

        return nested_dict

    @staticmethod
    def _to_python_type(val):
        """Convert numpy types to Python types for dict keys."""
        if hasattr(val, "item"):
            return val.item()
        return val

    def get_nested_dict(self, name: str) -> dict:
        """Get the nested dict for a specific dataset."""
        if name not in self._nested_dicts:
            raise KeyError(f"Dataset '{name}' not found.")

        return self._nested_dicts[name]

    def get_all_nested_dicts(self) -> dict:
        """Get all nested dicts."""
        return self._nested_dicts

    def get_dataset_info(self, name: str) -> dict:
        """Get dataset classification info."""
        if name not in self._dataset_info:
            raise KeyError(f"Dataset '{name}' not found.")

        return self._dataset_info[name]

    def get_series_data(
        self,
        dataset_name: str,
        var_name: str,
        series_val: str | int | float | None = None
    ) -> xr.DataArray:
        """Get 1D time series data for a specific variable and series."""
        if dataset_name not in self.datasets:
            raise KeyError(f"Dataset '{dataset_name}' not found.")

        ds = self.datasets[dataset_name]
        da = ds[var_name]
        ds_info = self._dataset_info[dataset_name]
        shape_type = ds_info["shape_type"]

        if shape_type == "time_only":
            return da

        if series_val is None:
            raise ValueError(f"series_val required for dataset '{dataset_name}'")

        return da.sel({ds_info["series_dim"]: series_val})

    def get_vars_with_qc_flags(self, name: str) -> dict[str, bool]:
        """Find variables that have an associated QC flag variable with valid data."""
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
        """Get all QC flag dicts."""
        return {name: self.get_vars_with_qc_flags(name) for name in self.datasets}

    def __repr__(self) -> str:
        datasets_info = ", ".join(self.datasets.keys()) if self.datasets else "None"
        time_info = f"{self.time_range}" if self.time_range else "Not set"
        return f"DatasetManager(datasets=[{datasets_info}], time_range={time_info})"