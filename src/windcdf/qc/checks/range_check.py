"""Range check - validates values are within physical limits."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from windcdf.qc.checks._base import BaseCheck
from windcdf.models.flags import Flag, FlagSeverity, FlagReason

if TYPE_CHECKING:
    import xarray as xr


# Default ranges for common variables
DEFAULT_RANGES = {
    "wind_speed": (0.0, 75.0),
    "wind_direction": (0.0, 360.0),
    "temperature": (-60.0, 60.0),
    "pressure": (800.0, 1100.0),
    "humidity": (0.0, 100.0),
}


class RangeCheck(BaseCheck):
    """Check that values fall within valid physical ranges."""

    @property
    def name(self) -> str:
        return "range_check"

    @property
    def description(self) -> str:
        return "Validates that values are within physically plausible limits"

    def run(
        self,
        variable: str,
        data: xr.DataArray,
        config: dict,
    ) -> list[Flag]:
        """Run range check."""
        flags = []

        # Get range limits from config or defaults
        var_lower = variable.lower()
        default_range = DEFAULT_RANGES.get(var_lower, (None, None))

        min_val = self.get_config_value(config, f"{variable}_min", default_range[0])
        max_val = self.get_config_value(config, f"{variable}_max", default_range[1])

        if min_val is None and max_val is None:
            return flags  # No range defined

        values = data.values
        time_dim = data.dims[0] if data.dims else None

        if time_dim and time_dim in data.coords:
            times = pd.to_datetime(data.coords[time_dim].values)
        else:
            times = [None] * len(values)

        for i, (val, time) in enumerate(zip(values, times)):
            if np.isnan(val):
                continue

            if min_val is not None and val < min_val:
                flags.append(Flag(
                    timestamp=time,
                    variable=variable,
                    severity=FlagSeverity.BAD,
                    reason=FlagReason.RANGE_CHECK,
                    check_name=self.name,
                    message=f"Value {val} below minimum {min_val}",
                ))
            elif max_val is not None and val > max_val:
                flags.append(Flag(
                    timestamp=time,
                    variable=variable,
                    severity=FlagSeverity.BAD,
                    reason=FlagReason.RANGE_CHECK,
                    check_name=self.name,
                    message=f"Value {val} above maximum {max_val}",
                ))

        return flags
