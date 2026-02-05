"""QC flag overlay for plots."""

from __future__ import annotations

from typing import TYPE_CHECKING

from windcdf.models.flags import FlagSeverity

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from windcdf.models.report import QCReport
    from windcdf.models.timeseries import TimeSeries


# Colors for flag severity levels
FLAG_COLORS = {
    FlagSeverity.GOOD: "#2ecc71",      # Green
    FlagSeverity.SUSPECT: "#f39c12",   # Orange
    FlagSeverity.BAD: "#e74c3c",       # Red
    FlagSeverity.MISSING: "#95a5a6",   # Gray
}

FLAG_MARKERS = {
    FlagSeverity.GOOD: "o",
    FlagSeverity.SUSPECT: "s",
    FlagSeverity.BAD: "x",
    FlagSeverity.MISSING: ".",
}


class QCOverlay:
    """Overlay QC flags on time series plots."""

    def __init__(self, report: QCReport) -> None:
        """Initialize overlay with QC report.

        Args:
            report: QC report with flags.
        """
        self.report = report

    def add_flags_to_plot(
        self,
        ax: Axes,
        ts: TimeSeries,
        severities: list[FlagSeverity] | None = None,
    ) -> None:
        """Add flag markers to a plot.

        Args:
            ax: Matplotlib axes.
            ts: Time series being plotted.
            severities: Severities to show (None = all).
        """
        import numpy as np

        flags = self.report.get_flags_for_variable(ts.name)
        if not flags:
            return

        if severities is None:
            severities = list(FlagSeverity)

        for severity in severities:
            severity_flags = [f for f in flags if f.severity == severity]
            if not severity_flags:
                continue

            # Find indices in time series
            flag_times = [f.timestamp for f in severity_flags]
            indices = []
            for ft in flag_times:
                if ft is None:
                    continue
                # Find closest time index
                ft_np = np.datetime64(ft)
                idx = np.argmin(np.abs(ts.time - ft_np))
                indices.append(idx)

            if indices:
                ax.scatter(
                    ts.time[indices],
                    ts.values[indices],
                    c=FLAG_COLORS[severity],
                    marker=FLAG_MARKERS[severity],
                    s=50,
                    label=f"{severity.name}",
                    zorder=5,
                )

    def add_flag_regions(
        self,
        ax: Axes,
        ts: TimeSeries,
        alpha: float = 0.2,
    ) -> None:
        """Add shaded regions for flagged periods.

        Args:
            ax: Matplotlib axes.
            ts: Time series being plotted.
            alpha: Transparency of shaded regions.
        """
        flags = self.report.get_flags_for_variable(ts.name)
        if not flags:
            return

        # Group consecutive flags
        for flag in flags:
            if flag.timestamp is None:
                continue

            # Add vertical span for bad flags
            if flag.severity == FlagSeverity.BAD:
                ax.axvline(
                    flag.timestamp,
                    color=FLAG_COLORS[FlagSeverity.BAD],
                    alpha=alpha,
                    linestyle="--",
                )
