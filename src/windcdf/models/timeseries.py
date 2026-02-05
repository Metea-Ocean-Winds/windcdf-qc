"""Normalized time series wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import xarray as xr
    from numpy.typing import NDArray


@dataclass
class TimeSeries:
    """Wrapper for time series data with associated metadata."""

    name: str
    time: NDArray[np.datetime64]
    values: NDArray[np.floating]
    units: str = ""
    attributes: dict = field(default_factory=dict)

    @classmethod
    def from_dataarray(cls, da: xr.DataArray, time_dim: str = "time") -> TimeSeries:
        """Create TimeSeries from xarray DataArray.

        Args:
            da: xarray DataArray with time dimension.
            time_dim: Name of the time dimension.

        Returns:
            TimeSeries instance.
        """
        return cls(
            name=da.name or "unnamed",
            time=da[time_dim].values,
            values=da.values,
            units=da.attrs.get("units", ""),
            attributes=dict(da.attrs),
        )

    def __len__(self) -> int:
        """Number of data points."""
        return len(self.values)

    @property
    def start_time(self) -> np.datetime64:
        """First timestamp."""
        return self.time[0]

    @property
    def end_time(self) -> np.datetime64:
        """Last timestamp."""
        return self.time[-1]

    def get_value_at(self, index: int) -> float:
        """Get value at specific index."""
        return float(self.values[index])

    def get_time_at(self, index: int) -> np.datetime64:
        """Get timestamp at specific index."""
        return self.time[index]

    def slice(self, start_idx: int, end_idx: int) -> TimeSeries:
        """Return a sliced copy of the time series."""
        return TimeSeries(
            name=self.name,
            time=self.time[start_idx:end_idx],
            values=self.values[start_idx:end_idx],
            units=self.units,
            attributes=self.attributes.copy(),
        )
