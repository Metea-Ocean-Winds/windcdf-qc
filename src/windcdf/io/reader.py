"""NetCDF file reader with CF-conventions support."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xarray as xr


class NetCDFReader:
    """Reader for NetCDF files with wind measurement data."""

    def __init__(self, filepath: str | Path) -> None:
        """Initialize reader with file path.

        Args:
            filepath: Path to NetCDF file.
        """
        self.filepath = Path(filepath)
        self._dataset: xr.Dataset | None = None

    def open(self) -> xr.Dataset:
        """Open and return the dataset.

        Returns:
            xarray Dataset with decoded CF-time.
        """
        import xarray as xr

        self._dataset = xr.open_dataset(
            self.filepath,
            decode_times=True,
            decode_cf=True,
        )
        return self._dataset

    def close(self) -> None:
        """Close the dataset."""
        if self._dataset is not None:
            self._dataset.close()
            self._dataset = None

    def __enter__(self) -> NetCDFReader:
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()

    @property
    def dataset(self) -> xr.Dataset:
        """Get the opened dataset."""
        if self._dataset is None:
            raise RuntimeError("Dataset not opened. Call open() first.")
        return self._dataset

    def get_variables(self) -> list[str]:
        """Get list of data variable names."""
        return list(self.dataset.data_vars)

    def get_time_variable(self) -> str | None:
        """Get the name of the time dimension."""
        for dim in self.dataset.dims:
            if "time" in dim.lower():
                return dim
        return None
