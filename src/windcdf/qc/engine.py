"""QC Engine - orchestrates the QC pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from windcdf.qc.registry import CheckRegistry
from windcdf.models.report import QCReport

if TYPE_CHECKING:
    import xarray as xr
    from windcdf.qc.checks import BaseCheck


class QCEngine:
    """Main QC engine that runs checks on datasets."""

    def __init__(self, config: dict | None = None) -> None:
        """Initialize QC engine.

        Args:
            config: Configuration dictionary with thresholds and settings.
        """
        self.config = config or {}
        self.registry = CheckRegistry()
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """Register built-in QC checks."""
        from windcdf.qc.checks import (
            RangeCheck,
            SpikeCheck,
            StuckSensorCheck,
            GapCheck,
            RampRateCheck,
            WindDirectionWrapCheck,
        )

        self.registry.register(RangeCheck())
        self.registry.register(SpikeCheck())
        self.registry.register(StuckSensorCheck())
        self.registry.register(GapCheck())
        self.registry.register(RampRateCheck())
        self.registry.register(WindDirectionWrapCheck())

    def run(
        self,
        dataset: xr.Dataset,
        variables: list[str] | None = None,
        checks: list[str] | None = None,
    ) -> QCReport:
        """Run QC checks on dataset.

        Args:
            dataset: xarray Dataset to check.
            variables: List of variables to check (None = all).
            checks: List of check names to run (None = all).

        Returns:
            QCReport with results.
        """
        # Determine which variables to check
        vars_to_check = variables or list(dataset.data_vars)

        # Determine which checks to run
        checks_to_run = self.registry.get_checks(checks)

        # Initialize report
        report = QCReport(
            filepath=str(dataset.encoding.get("source", "unknown")),
            variables_checked=vars_to_check,
            checks_run=[c.name for c in checks_to_run],
        )

        # Run each check on each variable
        for var_name in vars_to_check:
            if var_name not in dataset:
                continue

            data_array = dataset[var_name]

            for check in checks_to_run:
                if check.is_applicable(var_name, data_array):
                    flags = check.run(var_name, data_array, self.config)
                    for flag in flags:
                        report.add_flag(flag)

        return report

    def run_single_check(
        self,
        check_name: str,
        dataset: xr.Dataset,
        variable: str,
    ) -> list:
        """Run a single check on one variable.

        Args:
            check_name: Name of check to run.
            dataset: xarray Dataset.
            variable: Variable name.

        Returns:
            List of flags.
        """
        check = self.registry.get_check(check_name)
        if check is None:
            raise ValueError(f"Unknown check: {check_name}")

        return check.run(variable, dataset[variable], self.config)
