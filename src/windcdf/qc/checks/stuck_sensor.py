"""Stuck sensor detection check."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from windcdf.qc.checks._base import BaseCheck
from windcdf.models.flags import Flag, FlagSeverity, FlagReason

if TYPE_CHECKING:
    import xarray as xr


class StuckSensorCheck(BaseCheck):
    """Detect periods where sensor reports constant values."""

    @property
    def name(self) -> str:
        return "stuck_sensor"

    @property
    def description(self) -> str:
        return "Identifies sequences of identical values indicating sensor freeze"

    def run(
        self,
        variable: str,
        data: xr.DataArray,
        config: dict,
    ) -> list[Flag]:
        """Run stuck sensor detection."""
        flags = []

        # Configuration
        min_stuck_count = self.get_config_value(config, "min_stuck_count", 6)
        tolerance = self.get_config_value(config, "tolerance", 1e-6)

        values = data.values
        if len(values) < min_stuck_count:
            return flags

        time_dim = data.dims[0] if data.dims else None
        if time_dim and time_dim in data.coords:
            times = pd.to_datetime(data.coords[time_dim].values)
        else:
            times = [None] * len(values)

        # Find sequences of constant values
        i = 0
        while i < len(values):
            if np.isnan(values[i]):
                i += 1
                continue

            # Count consecutive identical values
            j = i + 1
            while j < len(values) and abs(values[j] - values[i]) < tolerance:
                j += 1

            stuck_count = j - i

            if stuck_count >= min_stuck_count:
                # Flag all points in the stuck sequence
                for k in range(i, j):
                    flags.append(Flag(
                        timestamp=times[k],
                        variable=variable,
                        severity=FlagSeverity.SUSPECT,
                        reason=FlagReason.STUCK_SENSOR,
                        check_name=self.name,
                        message=f"Stuck sensor: {stuck_count} identical values",
                    ))

            i = j

        return flags
