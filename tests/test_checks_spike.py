"""Tests for spike check."""

import pytest
import numpy as np


class TestSpikeCheck:
    """Test suite for SpikeCheck."""

    def test_spike_check_detects_spikes(self, sample_dataset_with_spikes):
        """Test that spikes are detected."""
        from windcdf.qc.checks.spike_check import SpikeCheck
        from windcdf.models.flags import FlagSeverity

        check = SpikeCheck()
        flags = check.run(
            "wind_speed",
            sample_dataset_with_spikes["wind_speed"],
            {},
        )

        # Should detect at least the obvious spikes
        assert len(flags) > 0
        assert all(f.severity == FlagSeverity.BAD for f in flags)

    def test_spike_check_with_clean_data(self, sample_dataset):
        """Test with clean data (may have some noise flags)."""
        from windcdf.qc.checks.spike_check import SpikeCheck

        check = SpikeCheck()
        # Use a constant dataset for clean test
        sample_dataset["wind_speed"].values[:] = 10.0

        flags = check.run("wind_speed", sample_dataset["wind_speed"], {})

        # Constant data should have no spikes
        assert len(flags) == 0
