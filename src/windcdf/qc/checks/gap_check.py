"""Gap detection check."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from windcdf.qc.checks._base import BaseCheck
from windcdf.models.flags import Flag, FlagSeverity, FlagReason

if TYPE_CHECKING:
    import xarray as xr


class GapCheck(BaseCheck):
    """Detect gaps in time series data."""

    @property
    def name(self) -> str:
        return "gap_check"

    @property
    def description(self) -> str:
        return "Identifies missing data and unexpected gaps"

    def run(
        self,
        variable: str,
        data: xr.DataArray,
        config: dict,
    ) -> list[Flag]:
        """Run gap detection."""
        flags = []

        # Configuration: max allowed gap as multiple of median interval
        gap_multiplier = self.get_config_value(config, "gap_multiplier", 2.0)

        time_dim = data.dims[0] if data.dims else None
        if not time_dim or time_dim not in data.coords:
            return flags

        times = pd.to_datetime(data.coords[time_dim].values)
        values = data.values

        # Flag NaN/missing values
        for i, (val, time) in enumerate(zip(values, times)):
            if np.isnan(val):
                flags.append(Flag(
                    timestamp=time,
                    variable=variable,
                    severity=FlagSeverity.MISSING,
                    reason=FlagReason.GAP,
                    check_name=self.name,
                    message="Missing value (NaN)",
                ))

        # Check for time gaps
        if len(times) < 2:
            return flags

        time_diffs = np.diff(times)
        median_diff = np.median(time_diffs)

        for i in range(1, len(times)):
            diff = times[i] - times[i - 1]
            if diff > median_diff * gap_multiplier:
                flags.append(Flag(
                    timestamp=times[i],
                    variable=variable,
                    severity=FlagSeverity.SUSPECT,
                    reason=FlagReason.GAP,
                    check_name=self.name,
                    message=f"Time gap detected: {diff}",
                ))

        return flags
