"""Session controller - manages file loading and state."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from windcdf.gui.app import WindCDFApp


class SessionController:
    """Controller for managing user session and data loading."""

    def __init__(self, app: WindCDFApp) -> None:
        """Initialize session controller.

        Args:
            app: Main application instance.
        """
        self.app = app

    def load_file(self, filepath: str | Path) -> bool:
        """Load a NetCDF file.

        Args:
            filepath: Path to file.

        Returns:
            True if successful.
        """
        from windcdf.io.reader import NetCDFReader

        try:
            reader = NetCDFReader(filepath)
            self.app.state.dataset = reader.open()
            self.app.state.filepath = str(filepath)
            return True
        except Exception:
            return False

    def close_file(self) -> None:
        """Close current file and reset state."""
        if self.app.state.dataset is not None:
            self.app.state.dataset.close()
        self.app.state.reset()

    def get_variables(self) -> list[str]:
        """Get list of variables in current dataset."""
        if self.app.state.dataset is None:
            return []
        return list(self.app.state.dataset.data_vars)

    def save_session(self, filepath: str | Path) -> bool:
        """Save current session state.

        Args:
            filepath: Path for session file.

        Returns:
            True if successful.
        """
        import json

        try:
            session_data = {
                "filepath": self.app.state.filepath,
                "selected_variables": self.app.state.selected_variables,
            }
            with open(filepath, "w") as f:
                json.dump(session_data, f)
            return True
        except Exception:
            return False

    def load_session(self, filepath: str | Path) -> bool:
        """Load session from file.

        Args:
            filepath: Path to session file.

        Returns:
            True if successful.
        """
        import json

        try:
            with open(filepath) as f:
                session_data = json.load(f)

            if session_data.get("filepath"):
                self.load_file(session_data["filepath"])
                self.app.state.selected_variables = session_data.get(
                    "selected_variables", []
                )
            return True
        except Exception:
            return False
