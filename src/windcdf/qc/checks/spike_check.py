"""Spike detection check."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from windcdf.qc.checks._base import BaseCheck
from windcdf.models.flags import Flag, FlagSeverity, FlagReason

if TYPE_CHECKING:
    import xarray as xr


class SpikeCheck(BaseCheck):
    """Detect sudden spikes in time series data."""

    @property
    def name(self) -> str:
        return "spike_check"

    @property
    def description(self) -> str:
        return "Identifies sudden unrealistic jumps in values"

    def run(
        self,
        variable: str,
        data: xr.DataArray,
        config: dict,
    ) -> list[Flag]:
        """Run spike detection."""
        flags = []

        # Configuration
        window_size = self.get_config_value(config, "window_size", 5)
        threshold_multiplier = self.get_config_value(config, "threshold_multiplier", 3.0)

        values = data.values
        if len(values) < window_size:
            return flags

        time_dim = data.dims[0] if data.dims else None
        if time_dim and time_dim in data.coords:
            times = pd.to_datetime(data.coords[time_dim].values)
        else:
            times = [None] * len(values)

        # Calculate rolling statistics
        for i in range(window_size, len(values) - 1):
            window = values[i - window_size:i]
            window = window[~np.isnan(window)]

            if len(window) < 2:
                continue

            mean = np.mean(window)
            std = np.std(window)

            if std == 0:
                continue

            # Check if next value is a spike
            next_val = values[i]
            if np.isnan(next_val):
                continue

            z_score = abs(next_val - mean) / std

            if z_score > threshold_multiplier:
                flags.append(Flag(
                    timestamp=times[i],
                    variable=variable,
                    severity=FlagSeverity.BAD,
                    reason=FlagReason.SPIKE,
                    check_name=self.name,
                    message=f"Spike detected: z-score={z_score:.2f}",
                ))

        return flags
