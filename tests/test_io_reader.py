"""Tests for NetCDF reader."""

import pytest
from pathlib import Path


class TestNetCDFReader:
    """Test suite for NetCDFReader."""

    def test_reader_initialization(self):
        """Test reader can be initialized."""
        from windcdf.io.reader import NetCDFReader

        reader = NetCDFReader("test.nc")
        assert reader.filepath == Path("test.nc")

    def test_get_variables(self, sample_dataset, tmp_path):
        """Test getting variable names."""
        from windcdf.io.reader import NetCDFReader

        # Save sample dataset
        filepath = tmp_path / "test.nc"
        sample_dataset.to_netcdf(filepath)

        reader = NetCDFReader(filepath)
        reader.open()
        variables = reader.get_variables()

        assert "wind_speed" in variables
        assert "wind_direction" in variables
        reader.close()
