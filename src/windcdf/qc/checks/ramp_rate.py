"""Ramp rate check - rate of change limits."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from windcdf.qc.checks._base import BaseCheck
from windcdf.models.flags import Flag, FlagSeverity, FlagReason

if TYPE_CHECKING:
    import xarray as xr


# Default max ramp rates (per second)
DEFAULT_RAMP_RATES = {
    "wind_speed": 5.0 / 600,  # 5 m/s per 10 minutes
    "temperature": 5.0 / 3600,  # 5°C per hour
    "pressure": 10.0 / 3600,  # 10 hPa per hour
}


class RampRateCheck(BaseCheck):
    """Check for excessive rates of change."""

    @property
    def name(self) -> str:
        return "ramp_rate"

    @property
    def description(self) -> str:
        return "Flags values with physically implausible rates of change"

    def run(
        self,
        variable: str,
        data: xr.DataArray,
        config: dict,
    ) -> list[Flag]:
        """Run ramp rate check."""
        flags = []

        var_lower = variable.lower()
        default_rate = DEFAULT_RAMP_RATES.get(var_lower)
        max_rate = self.get_config_value(config, f"{variable}_max_rate", default_rate)

        if max_rate is None:
            return flags

        values = data.values
        if len(values) < 2:
            return flags

        time_dim = data.dims[0] if data.dims else None
        if not time_dim or time_dim not in data.coords:
            return flags

        times = pd.to_datetime(data.coords[time_dim].values)

        for i in range(1, len(values)):
            if np.isnan(values[i]) or np.isnan(values[i - 1]):
                continue

            time_diff = (times[i] - times[i - 1]).total_seconds()
            if time_diff == 0:
                continue

            value_diff = abs(values[i] - values[i - 1])
            rate = value_diff / time_diff

            if rate > max_rate:
                flags.append(Flag(
                    timestamp=times[i],
                    variable=variable,
                    severity=FlagSeverity.SUSPECT,
                    reason=FlagReason.RAMP_RATE,
                    check_name=self.name,
                    message=f"Excessive ramp rate: {rate:.4f}/s (max: {max_rate:.4f}/s)",
                ))

        return flags
