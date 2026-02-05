"""Pytest configuration and fixtures."""

import pytest
import numpy as np
import xarray as xr


@pytest.fixture
def sample_dataset():
    """Create a sample dataset for testing."""
    time = np.arange("2024-01-01", "2024-01-02", dtype="datetime64[h]")
    wind_speed = np.random.uniform(0, 20, len(time))
    wind_direction = np.random.uniform(0, 360, len(time))

    ds = xr.Dataset(
        {
            "wind_speed": (["time"], wind_speed),
            "wind_direction": (["time"], wind_direction),
        },
        coords={"time": time},
    )
    return ds


@pytest.fixture
def sample_dataset_with_spikes(sample_dataset):
    """Create dataset with spike anomalies."""
    ds = sample_dataset.copy()
    # Add spikes
    ds["wind_speed"].values[10] = 100.0
    ds["wind_speed"].values[15] = -10.0
    return ds


@pytest.fixture
def sample_dataset_with_stuck_sensor(sample_dataset):
    """Create dataset with stuck sensor."""
    ds = sample_dataset.copy()
    # Add stuck values
    ds["wind_speed"].values[5:15] = 5.0
    return ds
