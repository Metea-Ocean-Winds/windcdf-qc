"""Time series plotting utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
    from windcdf.models.timeseries import TimeSeries


class TimeSeriesPlot:
    """Time series plotting helper."""

    def __init__(self, figsize: tuple[int, int] = (12, 6)) -> None:
        """Initialize plotter.

        Args:
            figsize: Figure size in inches.
        """
        self.figsize = figsize
        self._fig: Figure | None = None
        self._ax: Axes | None = None

    def create_figure(self) -> tuple[Figure, Axes]:
        """Create new figure and axes.

        Returns:
            Tuple of (figure, axes).
        """
        import matplotlib.pyplot as plt

        self._fig, self._ax = plt.subplots(figsize=self.figsize)
        return self._fig, self._ax

    def plot_timeseries(
        self,
        ts: TimeSeries,
        ax: Axes | None = None,
        **kwargs,
    ) -> Axes:
        """Plot a time series.

        Args:
            ts: TimeSeries object to plot.
            ax: Axes to plot on (creates new if None).
            **kwargs: Additional plot arguments.

        Returns:
            Axes with plot.
        """
        if ax is None:
            _, ax = self.create_figure()

        ax.plot(ts.time, ts.values, label=ts.name, **kwargs)
        ax.set_xlabel("Time")
        ax.set_ylabel(f"{ts.name} ({ts.units})" if ts.units else ts.name)
        ax.legend()

        return ax

    def plot_multiple(
        self,
        series_list: list[TimeSeries],
        share_x: bool = True,
    ) -> Figure:
        """Plot multiple time series.

        Args:
            series_list: List of TimeSeries to plot.
            share_x: Whether to share x-axis.

        Returns:
            Figure with subplots.
        """
        import matplotlib.pyplot as plt

        n = len(series_list)
        fig, axes = plt.subplots(n, 1, figsize=(self.figsize[0], 4 * n), sharex=share_x)

        if n == 1:
            axes = [axes]

        for ax, ts in zip(axes, series_list):
            self.plot_timeseries(ts, ax=ax)

        fig.tight_layout()
        return fig

    def save(self, filepath: str, **kwargs) -> None:
        """Save current figure.

        Args:
            filepath: Output path.
            **kwargs: Additional savefig arguments.
        """
        if self._fig is not None:
            self._fig.savefig(filepath, **kwargs)
