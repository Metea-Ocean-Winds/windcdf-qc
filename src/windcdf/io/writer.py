"""NetCDF file writer for flags and reports."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xarray as xr
    from windcdf.models.report import QCReport


class NetCDFWriter:
    """Writer for exporting QC results and cleaned data."""

    def __init__(self, filepath: str | Path) -> None:
        """Initialize writer with output path.

        Args:
            filepath: Path for output file.
        """
        self.filepath = Path(filepath)

    def write_dataset(self, dataset: xr.Dataset) -> None:
        """Write dataset to NetCDF file.

        Args:
            dataset: xarray Dataset to write.
        """
        dataset.to_netcdf(self.filepath)

    def write_flags(
        self,
        dataset: xr.Dataset,
        flags: dict[str, xr.DataArray],
    ) -> None:
        """Write dataset with QC flags added.

        Args:
            dataset: Original dataset.
            flags: Dictionary of flag arrays keyed by variable name.
        """
        ds_with_flags = dataset.copy()
        for var_name, flag_array in flags.items():
            ds_with_flags[f"{var_name}_qc_flag"] = flag_array
        ds_with_flags.to_netcdf(self.filepath)

    def export_report_json(self, report: QCReport, filepath: str | Path) -> None:
        """Export QC report to JSON.

        Args:
            report: QC report object.
            filepath: Output JSON path.
        """
        import json

        with open(filepath, "w") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)

    def export_flags_csv(
        self,
        flags: dict[str, xr.DataArray],
        filepath: str | Path,
    ) -> None:
        """Export flags to CSV format.

        Args:
            flags: Dictionary of flag arrays.
            filepath: Output CSV path.
        """
        import pandas as pd

        df = pd.DataFrame({name: arr.values for name, arr in flags.items()})
        df.to_csv(filepath, index=True)
