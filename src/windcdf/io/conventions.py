"""CF Conventions helpers for variable naming and metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xarray as xr


# Standard variable names following CF conventions
STANDARD_NAMES = {
    "wind_speed": "wind_speed",
    "wind_direction": "wind_from_direction",
    "temperature": "air_temperature",
    "pressure": "air_pressure",
    "humidity": "relative_humidity",
}

# Expected units for standard variables
EXPECTED_UNITS = {
    "wind_speed": "m s-1",
    "wind_direction": "degree",
    "temperature": "K",
    "pressure": "Pa",
    "humidity": "1",
}


class CFConventions:
    """Helper class for CF conventions compliance."""

    @staticmethod
    def get_standard_name(variable: str) -> str | None:
        """Get CF standard name for a variable.

        Args:
            variable: Variable name or alias.

        Returns:
            CF standard name or None if not found.
        """
        return STANDARD_NAMES.get(variable.lower())

    @staticmethod
    def validate_units(dataset: xr.Dataset, variable: str) -> bool:
        """Check if variable has expected units.

        Args:
            dataset: xarray Dataset.
            variable: Variable name to check.

        Returns:
            True if units are valid or not specified.
        """
        if variable not in dataset:
            return False

        var_attrs = dataset[variable].attrs
        if "units" not in var_attrs:
            return True  # No units specified, cannot validate

        # Check against expected units (simplified)
        expected = EXPECTED_UNITS.get(variable.lower())
        if expected is None:
            return True

        return var_attrs["units"] == expected

    @staticmethod
    def add_qc_flag_attributes(flag_array: xr.DataArray, variable: str) -> xr.DataArray:
        """Add CF-compliant attributes to a QC flag array.

        Args:
            flag_array: DataArray containing QC flags.
            variable: Name of the variable being flagged.

        Returns:
            DataArray with added attributes.
        """
        flag_array.attrs.update({
            "long_name": f"Quality control flags for {variable}",
            "standard_name": "quality_flag",
            "flag_values": [0, 1, 2, 3],
            "flag_meanings": "good suspect bad missing",
        })
        return flag_array
