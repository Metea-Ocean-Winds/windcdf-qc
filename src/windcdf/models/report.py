"""QC Report data structure and serialization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from windcdf.models.flags import Flag


@dataclass
class QCReport:
    """Container for QC results."""

    filepath: str
    created_at: datetime = field(default_factory=datetime.now)
    variables_checked: list[str] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def total_flags(self) -> int:
        """Total number of flags."""
        return len(self.flags)

    @property
    def flags_by_severity(self) -> dict[str, int]:
        """Count flags by severity level."""
        from collections import Counter
        return dict(Counter(f.severity.name for f in self.flags))

    @property
    def flags_by_check(self) -> dict[str, int]:
        """Count flags by check name."""
        from collections import Counter
        return dict(Counter(f.check_name for f in self.flags))

    def add_flag(self, flag: Flag) -> None:
        """Add a flag to the report."""
        self.flags.append(flag)

    def get_flags_for_variable(self, variable: str) -> list[Flag]:
        """Get all flags for a specific variable."""
        return [f for f in self.flags if f.variable == variable]

    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "filepath": self.filepath,
            "created_at": self.created_at.isoformat(),
            "variables_checked": self.variables_checked,
            "checks_run": self.checks_run,
            "total_flags": self.total_flags,
            "flags_by_severity": self.flags_by_severity,
            "flags_by_check": self.flags_by_check,
            "flags": [f.to_dict() for f in self.flags],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> QCReport:
        """Create report from dictionary."""
        from windcdf.models.flags import Flag

        report = cls(
            filepath=data["filepath"],
            created_at=datetime.fromisoformat(data["created_at"]),
            variables_checked=data.get("variables_checked", []),
            checks_run=data.get("checks_run", []),
            metadata=data.get("metadata", {}),
        )
        report.flags = [Flag.from_dict(f) for f in data.get("flags", [])]
        return report
