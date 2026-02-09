import xarray as xr
import pandas as pd


class DatasetManager:
    """Manages xr.Datasets with time range clipping and nested dict generation.
    
    The first added dataset sets the reference time range.
    Subsequent datasets can be clipped to this time range.
    
    Dataset dimension rules:
    - `time` only → single series per variable
    - `time + 1 extra dim` → series dimension splits variables
    - `time + 2 extra dims` → user selects series dim, other is source dim
    - `time + more than 2 extra dims` → reject dataset (raise error)
    """
    
    def __init__(self, time_dim: str = "time"):
        """Initialize the DatasetManager.
        
        Parameters
        ----------
        time_dim : str, optional
            Name of the time dimension, by default "time".
        """
        self.time_dim = time_dim
        self.datasets: dict[str, xr.Dataset] = {}
        self.time_range: tuple | None = None
        self._nested_dicts: dict[str, dict] = {}
        self._dataset_info: dict[str, dict] = {}  # stores dim info per dataset
    
    def _get_extra_dims(self, ds: xr.Dataset) -> list[str]:
        """Get extra dimensions (excluding time) for a Dataset."""
        return [dim for dim in ds.dims if dim != self.time_dim]
    
    def _validate_dataset(self, ds: xr.Dataset, name: str, series_dim: str | None = None) -> dict:
        """Validate dataset and classify its structure.
        
        Parameters
        ----------
        ds : xr.Dataset
            The dataset to validate.
        name : str
            Name identifier for error messages.
        series_dim : str, optional
            For 2 extra dims, which dimension is the series dimension.
            
        Returns
        -------
        dict
            Dataset info with shape_type, series_dim, source_dim.
            
        Raises
        ------
        ValueError
            If the dataset is missing the time dimension, time is not 1D,
            or has more than 2 extra dimensions.
        """
        # Must have time dimension
        if self.time_dim not in ds.dims:
            raise ValueError(f"Dataset '{name}' is missing required '{self.time_dim}' dimension")
        
        # Time must be 1D
        if ds[self.time_dim].ndim != 1:
            raise ValueError(f"Dataset '{name}': time dimension must be 1D")
        
        extra_dims = self._get_extra_dims(ds)
        n_extra = len(extra_dims)
        
        # Reject if more than 2 extra dimensions
        if n_extra > 2:
            raise ValueError(
                f"Dataset '{name}' has {n_extra} extra dimensions {extra_dims}. "
                f"Maximum allowed is 2 (time + 2 extra dims)."
            )
        
        if n_extra == 0:
            return {
                "extra_dims": [],
                "series_dim": None,
                "source_dim": None,
                "shape_type": "time_only"
            }
        elif n_extra == 1:
            return {
                "extra_dims": extra_dims,
                "series_dim": extra_dims[0],
                "source_dim": None,
                "shape_type": "time_plus_1"
            }
        else:  # n_extra == 2
            if series_dim is None:
                # Default: first extra dim is series, second is source
                series_dim = extra_dims[0]
            
            if series_dim not in extra_dims:
                raise ValueError(
                    f"series_dim '{series_dim}' not in dataset dimensions: {extra_dims}"
                )
            
            source_dim = [d for d in extra_dims if d != series_dim][0]
            
            return {
                "extra_dims": extra_dims,
                "series_dim": series_dim,
                "source_dim": source_dim,
                "shape_type": "time_plus_2"
            }
    
    def _is_valid_variable(self, var_name: str, da: xr.DataArray) -> bool:
        """Check if a variable is valid for QC.
        
        A variable is valid if:
        - it depends on time
        - it is not all NaN
        - it does not end with '_qcflag'
        """
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
        """Add a dataset to the manager.
        
        Parameters
        ----------
        name : str
            Name identifier for the dataset.
        ds : xr.Dataset
            The xarray Dataset to add.
        set_time_range : bool, optional
            If True, set the time range from this dataset. 
            Automatically True for the first dataset.
        series_dim : str, optional
            For datasets with 2 extra dims, specifies which dim is the series dim.
            The other dimension becomes the source dim.
            
        Raises
        ------
        ValueError
            If dataset has more than 2 extra dimensions beyond time.
        """
        # Validate dataset structure and get info
        ds_info = self._validate_dataset(ds, name, series_dim)
        
        # First dataset sets the time range
        if not self.datasets or set_time_range:
            self._set_time_range(ds)
        
        self.datasets[name] = ds
        self._dataset_info[name] = ds_info
        
        # Generate nested dict for this dataset
        self._nested_dicts[name] = self._generate_nested_dict(ds, ds_info, name)
    
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
        clipped = self.datasets[name].sel({self.time_dim: slice(first_time, last_time)})
        return clipped
    
    def _generate_nested_dict(self, ds: xr.Dataset, ds_info: dict, dataset_name: str = "unknown") -> dict:
        """Generate nested dict: source -> series_value -> [variables].
        
        Structure depends on dataset shape:
        - time_only: source=from attrs or "default", series_value="all"
        - time_plus_1: if dim is "source" -> sources split, else series split
        - time_plus_2: source=source_dim values, series_value=series_dim values
        
        Only includes variables that are valid (time-dependent, not all NaN).
        """
        shape_type = ds_info["shape_type"]
        nested_dict: dict = {}
        
        # Get valid variables
        valid_vars = [
            var for var in ds.data_vars 
            if self._is_valid_variable(var, ds[var])
        ]
        
        if shape_type == "time_only":
            # Use source from global attributes if available
            source_name = ds.attrs.get("source", dataset_name)
            if valid_vars:
                nested_dict[source_name] = {"all": valid_vars}
        
        elif shape_type == "time_plus_1":
            series_dim = ds_info["series_dim"]
            
            # Check if the single extra dimension is "source"
            if series_dim == "source":
                # Split by source, not by series - each source gets all variables
                for source_val in ds[series_dim].values:
                    source_key = self._to_python_type(source_val)
                    vars_at_source = [
                        var for var in valid_vars
                        if not ds[var].sel({series_dim: source_val}).isnull().all()
                    ]
                    if vars_at_source:
                        nested_dict[source_key] = {"all": vars_at_source}
            else:
                # Normal series dimension - split variables by series values
                source_name = ds.attrs.get("source", dataset_name)
                nested_dict[source_name] = {}
                
                for series_val in ds[series_dim].values:
                    key = self._to_python_type(series_val)
                    vars_at_series = [
                        var for var in valid_vars
                        if not ds[var].sel({series_dim: series_val}).isnull().all()
                    ]
                    if vars_at_series:
                        nested_dict[source_name][key] = vars_at_series
                
                # Remove empty source
                if not nested_dict[source_name]:
                    nested_dict = {}
        
        elif shape_type == "time_plus_2":
            series_dim = ds_info["series_dim"]
            source_dim = ds_info["source_dim"]
            
            for source_val in ds[source_dim].values:
                source_key = self._to_python_type(source_val)
                nested_dict[source_key] = {}
                
                for series_val in ds[series_dim].values:
                    series_key = self._to_python_type(series_val)
                    vars_at_slice = [
                        var for var in valid_vars
                        if not ds[var].sel(
                            {source_dim: source_val, series_dim: series_val}
                        ).isnull().all()
                    ]
                    if vars_at_slice:
                        nested_dict[source_key][series_key] = vars_at_slice
                
                # Remove empty sources
                if not nested_dict[source_key]:
                    del nested_dict[source_key]
        
        return nested_dict
    
    @staticmethod
    def _to_python_type(val):
        """Convert numpy types to Python types for use as dict keys."""
        if hasattr(val, "item"):
            return val.item()
        return val
    
    def get_nested_dict(self, name: str) -> dict:
        """Get the nested dict for a specific dataset."""
        if name not in self._nested_dicts:
            raise KeyError(f"Dataset '{name}' not found.")
        
        return self._nested_dicts[name]
    
    def get_all_nested_dicts(self) -> dict:
        """Get all nested dicts.
        
        Returns
        -------
        dict
            Dictionary with dataset names as keys and nested dicts as values.
        """
        return self._nested_dicts
    
    def get_dataset_info(self, name: str) -> dict:
        """Get dataset classification info.
        
        Parameters
        ----------
        name : str
            Name of the dataset.
            
        Returns
        -------
        dict
            Dictionary with shape_type, series_dim, source_dim, extra_dims.
        """
        if name not in self._dataset_info:
            raise KeyError(f"Dataset '{name}' not found.")
        
        return self._dataset_info[name]
    
    def get_series_data(
        self, 
        dataset_name: str, 
        var_name: str, 
        source_val: str | None = None,
        series_val: str | int | float | None = None
    ) -> xr.DataArray:
        """Get 1D time series data for a specific variable and series.
        
        Parameters
        ----------
        dataset_name : str
            Name of the dataset.
        var_name : str
            Name of the variable.
        source_val : str, optional
            Value along the source dimension (for time_plus_2 datasets).
        series_val : str, int, float, optional
            Value along the series dimension (for time_plus_1 or time_plus_2).
            
        Returns
        -------
        xr.DataArray
            1D DataArray with only time dimension.
        """
        if dataset_name not in self.datasets:
            raise KeyError(f"Dataset '{dataset_name}' not found.")
        
        ds = self.datasets[dataset_name]
        da = ds[var_name]
        ds_info = self._dataset_info[dataset_name]
        shape_type = ds_info["shape_type"]
        
        if shape_type == "time_only":
            return da
        
        elif shape_type == "time_plus_1":
            if series_val is None:
                raise ValueError(f"series_val required for dataset '{dataset_name}'")
            return da.sel({ds_info["series_dim"]: series_val})
        
        else:  # time_plus_2
            if source_val is None or series_val is None:
                raise ValueError(
                    f"Both source_val and series_val required for dataset '{dataset_name}'"
                )
            return da.sel({ds_info["source_dim"]: source_val, ds_info["series_dim"]: series_val})
    
    def get_vars_with_qc_flags(self, name: str) -> dict[str, dict[str, bool]]:
        """Find variables that have an associated QC flag variable with valid data.
        
        Parameters
        ----------
        name : str
            Name of the dataset.
        
        Returns
        -------
        dict[str, dict[str, bool]]
            Nested dictionary with source -> variable -> True.
        """
        if name not in self.datasets:
            raise KeyError(f"Dataset '{name}' not found.")
        
        ds = self.datasets[name]
        ds_info = self._dataset_info[name]
        
        all_vars = list(ds.data_vars)
        qc_flags = {var for var in all_vars if var.endswith("_qcflag")}
        
        # Get base variables that have QC flag variables
        base_vars_with_qc = [
            var for var in all_vars
            if not var.endswith("_qcflag") 
            and f"{var}_qcflag" in qc_flags
            and self._is_valid_variable(var, ds[var])
        ]
        
        result: dict[str, dict[str, bool]] = {}
        shape_type = ds_info["shape_type"]
        
        if shape_type == "time_only":
            source_name = ds.attrs.get("source", name)
            for var_name in base_vars_with_qc:
                qc_da = ds[f"{var_name}_qcflag"]
                if not qc_da.isnull().all():
                    if source_name not in result:
                        result[source_name] = {}
                    result[source_name][var_name] = True
        
        elif shape_type == "time_plus_1":
            series_dim = ds_info["series_dim"]
            if series_dim == "source":
                # Split by source
                for source_val in ds[series_dim].values:
                    source_key = self._to_python_type(source_val)
                    for var_name in base_vars_with_qc:
                        qc_da = ds[f"{var_name}_qcflag"]
                        sliced = qc_da.sel({series_dim: source_val})
                        if not sliced.isnull().all():
                            if source_key not in result:
                                result[source_key] = {}
                            result[source_key][var_name] = True
            else:
                # Normal series dimension
                source_name = ds.attrs.get("source", name)
                for var_name in base_vars_with_qc:
                    qc_da = ds[f"{var_name}_qcflag"]
                    if not qc_da.isnull().all():
                        if source_name not in result:
                            result[source_name] = {}
                        result[source_name][var_name] = True
        
        elif shape_type == "time_plus_2":
            source_dim = ds_info["source_dim"]
            
            for var_name in base_vars_with_qc:
                qc_da = ds[f"{var_name}_qcflag"]
                
                for source_val in ds[source_dim].values:
                    source_key = self._to_python_type(source_val)
                    sliced = qc_da.sel({source_dim: source_val})
                    
                    if not sliced.isnull().all():
                        if source_key not in result:
                            result[source_key] = {}
                        result[source_key][var_name] = True
        
        return result
    
    def get_all_vars_with_qc_flags(self) -> dict[str, dict[str, dict[str, bool]]]:
        """Get all QC flags dicts.
        
        Returns
        -------
        dict
            Dictionary with dataset names as keys and QC flags dicts as values.
        """
        return {name: self.get_vars_with_qc_flags(name) for name in self.datasets}
    
    def __repr__(self) -> str:
        datasets_info = ", ".join(self.datasets.keys()) if self.datasets else "None"
        time_info = f"{self.time_range}" if self.time_range else "Not set"
        return f"DatasetManager(datasets=[{datasets_info}], time_range={time_info})"