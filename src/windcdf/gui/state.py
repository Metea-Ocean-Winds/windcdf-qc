"""GUI state management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import xarray as xr
    from windcdf.models.report import QCReport


@dataclass
class AppState:
    """Application state container."""

    # Current dataset
    dataset: xr.Dataset | None = None
    filepath: str | None = None

    # Selected variables
    selected_variables: list[str] = field(default_factory=list)

    # Current QC report
    qc_report: QCReport | None = None

    # View state
    zoom_range: tuple[int, int] | None = None
    selected_indices: list[int] = field(default_factory=list)

    # Flags visibility
    show_good: bool = True
    show_suspect: bool = True
    show_bad: bool = True
    show_missing: bool = True

    def reset(self) -> None:
        """Reset state to initial values."""
        self.dataset = None
        self.filepath = None
        self.selected_variables = []
        self.qc_report = None
        self.zoom_range = None
        self.selected_indices = []

    def has_data(self) -> bool:
        """Check if data is loaded."""
        return self.dataset is not None

    def has_results(self) -> bool:
        """Check if QC results are available."""
        return self.qc_report is not None
