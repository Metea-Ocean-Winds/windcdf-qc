"""Tests for range check."""

import pytest
import numpy as np


class TestRangeCheck:
    """Test suite for RangeCheck."""

    def test_range_check_detects_out_of_range(self, sample_dataset):
        """Test that out of range values are flagged."""
        from windcdf.qc.checks.range_check import RangeCheck
        from windcdf.models.flags import FlagSeverity

        # Add out of range values
        ds = sample_dataset.copy()
        ds["wind_speed"].values[0] = 100.0  # Above max
        ds["wind_speed"].values[1] = -5.0   # Below min

        check = RangeCheck()
        flags = check.run("wind_speed", ds["wind_speed"], {})

        assert len(flags) == 2
        assert all(f.severity == FlagSeverity.BAD for f in flags)

    def test_range_check_passes_valid_data(self, sample_dataset):
        """Test that valid data passes."""
        from windcdf.qc.checks.range_check import RangeCheck

        check = RangeCheck()
        flags = check.run("wind_speed", sample_dataset["wind_speed"], {})

        # Should have no flags (random data is 0-20, which is valid)
        assert len(flags) == 0
