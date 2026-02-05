"""Base class for QC checks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xarray as xr
    from windcdf.models.flags import Flag


class BaseCheck(ABC):
    """Abstract base class for all QC checks."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this check."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the check."""
        ...

    @abstractmethod
    def run(
        self,
        variable: str,
        data: xr.DataArray,
        config: dict,
    ) -> list[Flag]:
        """Execute the check on data.

        Args:
            variable: Variable name being checked.
            data: xarray DataArray with time dimension.
            config: Configuration dictionary with thresholds.

        Returns:
            List of Flag objects for detected issues.
        """
        ...

    def is_applicable(self, variable: str, data: xr.DataArray) -> bool:
        """Check if this check applies to the given variable.

        Override in subclasses for variable-specific checks.

        Args:
            variable: Variable name.
            data: Data array.

        Returns:
            True if check should be run.
        """
        return True

    def get_config_value(
        self,
        config: dict,
        key: str,
        default: any,
    ) -> any:
        """Get configuration value with fallback to default.

        Args:
            config: Configuration dictionary.
            key: Configuration key.
            default: Default value if not found.

        Returns:
            Configuration value or default.
        """
        check_config = config.get(self.name, {})
        return check_config.get(key, default)
