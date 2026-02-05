"""Flag definitions and severity levels."""

from __future__ import annotations

from enum import IntEnum, IntFlag
from dataclasses import dataclass
from datetime import datetime


class FlagSeverity(IntEnum):
    """QC flag severity levels."""

    GOOD = 0
    SUSPECT = 1
    BAD = 2
    MISSING = 3


class FlagReason(IntFlag):
    """Bitmask for flag reasons (can be combined)."""

    NONE = 0
    RANGE_CHECK = 1 << 0
    SPIKE = 1 << 1
    STUCK_SENSOR = 1 << 2
    GAP = 1 << 3
    RAMP_RATE = 1 << 4
    DIRECTION_WRAP = 1 << 5
    MANUAL = 1 << 6


@dataclass
class Flag:
    """Represents a QC flag for a data point."""

    timestamp: datetime
    variable: str
    severity: FlagSeverity
    reason: FlagReason
    check_name: str
    message: str = ""
    auto_generated: bool = True

    def to_dict(self) -> dict:
        """Convert flag to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "variable": self.variable,
            "severity": self.severity.name,
            "reason": self.reason.name,
            "check_name": self.check_name,
            "message": self.message,
            "auto_generated": self.auto_generated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Flag:
        """Create Flag from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            variable=data["variable"],
            severity=FlagSeverity[data["severity"]],
            reason=FlagReason[data["reason"]],
            check_name=data["check_name"],
            message=data.get("message", ""),
            auto_generated=data.get("auto_generated", True),
        )
