"""QC controller - manages QC operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from windcdf.gui.app import WindCDFApp
    from windcdf.models.report import QCReport


class QCController:
    """Controller for QC operations."""

    def __init__(self, app: WindCDFApp) -> None:
        """Initialize QC controller.

        Args:
            app: Main application instance.
        """
        self.app = app

    def run_qc(
        self,
        variables: list[str] | None = None,
        checks: list[str] | None = None,
    ) -> QCReport | None:
        """Run QC checks.

        Args:
            variables: Variables to check (None = all selected).
            checks: Checks to run (None = all).

        Returns:
            QC report or None on error.
        """
        from windcdf.qc.engine import QCEngine

        if self.app.state.dataset is None:
            return None

        vars_to_check = variables or self.app.state.selected_variables
        if not vars_to_check:
            return None

        try:
            engine = QCEngine()
            report = engine.run(
                self.app.state.dataset,
                variables=vars_to_check,
                checks=checks,
            )
            self.app.state.qc_report = report
            return report
        except Exception:
            return None

    def accept_flag(self, flag_index: int) -> None:
        """Mark a flag as accepted (user confirmed).

        Args:
            flag_index: Index of flag in report.
        """
        if self.app.state.qc_report is None:
            return

        if 0 <= flag_index < len(self.app.state.qc_report.flags):
            self.app.state.qc_report.flags[flag_index].auto_generated = False

    def reject_flag(self, flag_index: int) -> None:
        """Remove a flag (user rejected).

        Args:
            flag_index: Index of flag to remove.
        """
        if self.app.state.qc_report is None:
            return

        if 0 <= flag_index < len(self.app.state.qc_report.flags):
            del self.app.state.qc_report.flags[flag_index]

    def export_report(self, filepath: str, format: str = "json") -> bool:
        """Export QC report.

        Args:
            filepath: Output path.
            format: Export format ('json' or 'csv').

        Returns:
            True if successful.
        """
        from windcdf.io.writer import NetCDFWriter

        if self.app.state.qc_report is None:
            return False

        try:
            writer = NetCDFWriter(filepath)
            if format == "json":
                writer.export_report_json(self.app.state.qc_report, filepath)
            return True
        except Exception:
            return False
