"""Data model classes for NetCDF handling and QC operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import xarray as xr


# QC flag definitions
QC_FLAGS = {
    0: ("good", None),              # No overlay color
    1: ("probably_good", "green"),
    2: ("probably_bad", "yellow"),
    3: ("bad", "red"),
    4: ("missing", "grey"),
    5: ("interpolated", "blue"),
}

QC_FLAG_VALUES = [0, 1, 2, 3, 4, 5]
QC_FLAG_MEANINGS = "good probably_good probably_bad bad missing interpolated"


@dataclass
class SeriesIdentifier:
    """Unique identifier for a plotted series."""
    dataset_id: str
    variable_name: str
    series_key: tuple[tuple[str, Any], ...] = field(default_factory=tuple)
    
    def __hash__(self) -> int:
        return hash((self.dataset_id, self.variable_name, self.series_key))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SeriesIdentifier):
            return False
        return (self.dataset_id == other.dataset_id and 
                self.variable_name == other.variable_name and 
                self.series_key == other.series_key)
    
    def get_display_name(self) -> str:
        """Get human-readable name for the series."""
        parts = [self.dataset_id, self.variable_name]
        if self.series_key:
            key_str = ", ".join(f"{k}={v}" for k, v in self.series_key)
            parts.append(f"[{key_str}]")
        return " / ".join(parts)


@dataclass
class UndoOperation:
    """Stores information needed to undo a QC flag operation."""
    series_id: SeriesIdentifier
    time_slice: slice
    previous_values: np.ndarray
    coord_slices: dict[str, Any] = field(default_factory=dict)


class DatasetManager:
    """Manages loaded NetCDF datasets and QC operations."""
    
    def __init__(self):
        self.datasets: dict[str, xr.Dataset] = {}
        self.dataset_paths: dict[str, str] = {}
        self.undo_stack: list[UndoOperation] = []
    
    def load_dataset(self, filepath: str, dataset_id: str | None = None) -> str:
        """Load a NetCDF dataset and return its ID."""
        import os
        
        if dataset_id is None:
            dataset_id = os.path.basename(filepath)
            # Ensure unique ID
            base_id = dataset_id
            counter = 1
            while dataset_id in self.datasets:
                dataset_id = f"{base_id}_{counter}"
                counter += 1
        
        ds = xr.open_dataset(filepath)
        
        # Validate time dimension
        if "time" not in ds.dims:
            ds.close()
            raise ValueError(f"Dataset {filepath} has no 'time' dimension")
        
        if len(ds["time"].dims) != 1:
            ds.close()
            raise ValueError(f"Dataset {filepath} has multi-dimensional time")
        
        self.datasets[dataset_id] = ds
        self.dataset_paths[dataset_id] = filepath
        return dataset_id
    
    def get_eligible_variables(self, dataset_id: str) -> list[str]:
        """Get list of variables eligible for QC flagging."""
        ds = self.datasets[dataset_id]
        eligible = []
        
        for var_name in ds.data_vars:
            var = ds[var_name]
            
            # Must depend on time
            if "time" not in var.dims:
                continue
            
            # Must not be all null
            if var.isnull().all():
                continue
            
            # Count extra dimensions (non-time)
            extra_dims = [d for d in var.dims if d != "time"]
            
            # Reject if more than 2 extra dimensions
            if len(extra_dims) > 2:
                continue
            
            # Skip QC flag variables themselves
            if var_name.endswith("_qcflag"):
                continue
            
            eligible.append(var_name)
        
        return eligible
    
    def get_variable_series(self, dataset_id: str, variable_name: str, 
                            series_dim: str | None = None) -> list[SeriesIdentifier]:
        """Get all series identifiers for a variable."""
        ds = self.datasets[dataset_id]
        var = ds[variable_name]
        
        extra_dims = [d for d in var.dims if d != "time"]
        
        if len(extra_dims) == 0:
            # Single series
            return [SeriesIdentifier(dataset_id, variable_name)]
        
        elif len(extra_dims) == 1:
            # One extra dimension - each value is a series
            dim = extra_dims[0]
            series = []
            for val in ds[dim].values:
                key = ((dim, val),)
                series.append(SeriesIdentifier(dataset_id, variable_name, key))
            return series
        
        elif len(extra_dims) == 2:
            # Two extra dimensions - user must select series_dim
            if series_dim is None:
                series_dim = extra_dims[0]  # Default to first
            
            fixed_dim = [d for d in extra_dims if d != series_dim][0]
            series = []
            
            # For each combination of series_dim value and first fixed_dim value
            for series_val in ds[series_dim].values:
                fixed_val = ds[fixed_dim].values[0]  # Use first value of fixed dim
                key = ((series_dim, series_val), (fixed_dim, fixed_val))
                series.append(SeriesIdentifier(dataset_id, variable_name, key))
            
            return series
        
        return []
    
    def ensure_qc_flag(self, dataset_id: str, variable_name: str) -> str:
        """Ensure QC flag variable exists for a variable, create if needed."""
        ds = self.datasets[dataset_id]
        var = ds[variable_name]
        qc_name = f"{variable_name}_qcflag"
        
        if qc_name in ds.data_vars:
            # Validate shape matches
            qc_var = ds[qc_name]
            if qc_var.dims != var.dims:
                raise ValueError(f"QC flag {qc_name} has mismatched dimensions")
            return qc_name
        
        # Create new QC flag variable
        qc_data = np.zeros(var.shape, dtype=np.uint8)
        qc_var = xr.DataArray(
            qc_data,
            dims=var.dims,
            coords={d: var.coords[d] for d in var.dims if d in var.coords},
            attrs={
                "flag_values": QC_FLAG_VALUES,
                "flag_meanings": QC_FLAG_MEANINGS,
                "long_name": f"quality flag for {variable_name}",
            }
        )
        
        ds[qc_name] = qc_var
        
        # Update original variable's ancillary_variables attribute
        ancillary = var.attrs.get("ancillary_variables", "")
        if qc_name not in ancillary:
            if ancillary:
                ancillary = f"{ancillary} {qc_name}"
            else:
                ancillary = qc_name
            ds[variable_name].attrs["ancillary_variables"] = ancillary
        
        return qc_name
    
    def get_series_data(
        self, series_id: SeriesIdentifier
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Get time, values, and QC flags for a series."""
        ds = self.datasets[series_id.dataset_id]
        var = ds[series_id.variable_name]
        qc_name = f"{series_id.variable_name}_qcflag"
        
        # Ensure QC flag exists
        self.ensure_qc_flag(series_id.dataset_id, series_id.variable_name)
        qc_var = ds[qc_name]
        
        # Apply coordinate selection
        sel_dict = {k: v for k, v in series_id.series_key}
        
        if sel_dict:
            var_sel = var.sel(**sel_dict)
            qc_sel = qc_var.sel(**sel_dict)
        else:
            var_sel = var
            qc_sel = qc_var
        
        time = ds["time"].values
        values = var_sel.values
        qc_flags = qc_sel.values
        
        return time, values, qc_flags
    
    def apply_qc_flag(self, series_id: SeriesIdentifier, 
                      time_start: np.datetime64, time_end: np.datetime64,
                      flag_value: int) -> None:
        """Apply QC flag to a time range, storing undo information."""
        ds = self.datasets[series_id.dataset_id]
        qc_name = f"{series_id.variable_name}_qcflag"
        
        self.ensure_qc_flag(series_id.dataset_id, series_id.variable_name)
        
        time = ds["time"].values
        
        # Find time indices
        mask = (time >= time_start) & (time <= time_end)
        indices = np.where(mask)[0]
        
        if len(indices) == 0:
            return
        
        time_slice = slice(indices[0], indices[-1] + 1)
        
        # Build selection for the series
        sel_dict = {k: v for k, v in series_id.series_key}
        
        # Get current values for undo
        if sel_dict:
            current_qc = ds[qc_name].sel(**sel_dict).isel(time=time_slice).values.copy()
        else:
            current_qc = ds[qc_name].isel(time=time_slice).values.copy()
        
        # Store undo operation
        undo_op = UndoOperation(
            series_id=series_id,
            time_slice=time_slice,
            previous_values=current_qc,
            coord_slices=sel_dict,
        )
        self.undo_stack.append(undo_op)
        
        # Apply new flag values
        # We need to modify in place
        qc_data = ds[qc_name].values
        
        # Build index for the full array
        if sel_dict:
            # Get dimension order
            dims = ds[qc_name].dims
            idx = []
            for dim in dims:
                if dim == "time":
                    idx.append(time_slice)
                elif dim in sel_dict:
                    # Find index of the coordinate value
                    coord_vals = ds[dim].values
                    coord_idx = np.where(coord_vals == sel_dict[dim])[0][0]
                    idx.append(coord_idx)
                else:
                    idx.append(slice(None))
            qc_data[tuple(idx)] = flag_value
        else:
            qc_data[time_slice] = flag_value
    
    def undo_last(self) -> SeriesIdentifier | None:
        """Undo the last QC flag operation. Returns the affected series ID."""
        if not self.undo_stack:
            return None
        
        undo_op = self.undo_stack.pop()
        ds = self.datasets[undo_op.series_id.dataset_id]
        qc_name = f"{undo_op.series_id.variable_name}_qcflag"
        
        qc_data = ds[qc_name].values
        sel_dict = undo_op.coord_slices
        
        if sel_dict:
            dims = ds[qc_name].dims
            idx = []
            for dim in dims:
                if dim == "time":
                    idx.append(undo_op.time_slice)
                elif dim in sel_dict:
                    coord_vals = ds[dim].values
                    coord_idx = np.where(coord_vals == sel_dict[dim])[0][0]
                    idx.append(coord_idx)
                else:
                    idx.append(slice(None))
            qc_data[tuple(idx)] = undo_op.previous_values
        else:
            qc_data[undo_op.time_slice] = undo_op.previous_values
        
        return undo_op.series_id
    
    def save_dataset(self, dataset_id: str, filepath: str) -> None:
        """Save a dataset to a NetCDF file."""
        ds = self.datasets[dataset_id]
        ds.to_netcdf(filepath)
    
    def get_time_bounds(self) -> tuple[np.datetime64, np.datetime64] | None:
        """Get the common time bounds across all datasets."""
        if not self.datasets:
            return None
        
        min_time = None
        max_time = None
        
        for ds in self.datasets.values():
            time = ds["time"].values
            ds_min = np.min(time)
            ds_max = np.max(time)
            
            if min_time is None:
                min_time = ds_min
                max_time = ds_max
            else:
                # Stage-2: datasets must share identical start/end
                # For now, we take intersection
                min_time = max(min_time, ds_min)
                max_time = min(max_time, ds_max)
        
        return min_time, max_time
    
    def close_all(self) -> None:
        """Close all datasets."""
        for ds in self.datasets.values():
            ds.close()
        self.datasets.clear()
        self.dataset_paths.clear()
        self.undo_stack.clear()
