"""Smoke tests for GUI."""

import pytest


class TestGUISmoke:
    """Minimal smoke tests for GUI components."""

    def test_app_state_initialization(self):
        """Test app state can be created."""
        from windcdf.gui.state import AppState

        state = AppState()
        assert state.dataset is None
        assert state.has_data() is False

    def test_app_state_reset(self):
        """Test app state reset."""
        from windcdf.gui.state import AppState

        state = AppState()
        state.filepath = "test.nc"
        state.reset()

        assert state.filepath is None

    # Note: Full GUI tests require display, which may not be available in CI
    # These would need to be run with xvfb or similar in headless environments
