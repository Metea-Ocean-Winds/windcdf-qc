"""Check registration and discovery."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from windcdf.qc.checks import BaseCheck


class CheckRegistry:
    """Registry for QC checks."""

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._checks: dict[str, BaseCheck] = {}

    def register(self, check: BaseCheck) -> None:
        """Register a check.

        Args:
            check: Check instance to register.
        """
        self._checks[check.name] = check

    def unregister(self, name: str) -> None:
        """Remove a check from registry.

        Args:
            name: Check name to remove.
        """
        if name in self._checks:
            del self._checks[name]

    def get_check(self, name: str) -> BaseCheck | None:
        """Get check by name.

        Args:
            name: Check name.

        Returns:
            Check instance or None.
        """
        return self._checks.get(name)

    def get_checks(self, names: list[str] | None = None) -> list[BaseCheck]:
        """Get multiple checks by name.

        Args:
            names: List of check names (None = all).

        Returns:
            List of check instances.
        """
        if names is None:
            return list(self._checks.values())
        return [self._checks[n] for n in names if n in self._checks]

    def list_checks(self) -> list[str]:
        """List all registered check names."""
        return list(self._checks.keys())

    def __contains__(self, name: str) -> bool:
        """Check if a check is registered."""
        return name in self._checks

    def __len__(self) -> int:
        """Number of registered checks."""
        return len(self._checks)
