"""Wind direction wrap check - handles 0°/360° discontinuity."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from windcdf.qc.checks._base import BaseCheck
from windcdf.models.flags import Flag, FlagSeverity, FlagReason

if TYPE_CHECKING:
    import xarray as xr


class WindDirectionWrapCheck(BaseCheck):
    """Check for wind direction continuity across 0°/360° boundary."""

    @property
    def name(self) -> str:
        return "wind_direction_wrap"

    @property
    def description(self) -> str:
        return "Validates wind direction continuity using circular statistics"

    def is_applicable(self, variable: str, data: xr.DataArray) -> bool:
        """Only applicable to direction variables."""
        var_lower = variable.lower()
        return "direction" in var_lower or "dir" in var_lower

    def run(
        self,
        variable: str,
        data: xr.DataArray,
        config: dict,
    ) -> list[Flag]:
        """Run wind direction wrap check."""
        flags = []

        # Configuration
        max_angular_change = self.get_config_value(config, "max_angular_change", 180.0)

        values = data.values
        if len(values) < 2:
            return flags

        time_dim = data.dims[0] if data.dims else None
        if time_dim and time_dim in data.coords:
            times = pd.to_datetime(data.coords[time_dim].values)
        else:
            times = [None] * len(values)

        for i in range(1, len(values)):
            if np.isnan(values[i]) or np.isnan(values[i - 1]):
                continue

            # Calculate angular difference (handling wrap)
            diff = self._angular_difference(values[i - 1], values[i])

            if abs(diff) > max_angular_change:
                flags.append(Flag(
                    timestamp=times[i],
                    variable=variable,
                    severity=FlagSeverity.SUSPECT,
                    reason=FlagReason.DIRECTION_WRAP,
                    check_name=self.name,
                    message=f"Large direction change: {diff:.1f}° (max: {max_angular_change}°)",
                ))

        return flags

    @staticmethod
    def _angular_difference(angle1: float, angle2: float) -> float:
        """Calculate the shortest angular difference between two angles.

        Args:
            angle1: First angle in degrees.
            angle2: Second angle in degrees.

        Returns:
            Signed angular difference in range [-180, 180].
        """
        diff = (angle2 - angle1) % 360
        if diff > 180:
            diff -= 360
        return diff
