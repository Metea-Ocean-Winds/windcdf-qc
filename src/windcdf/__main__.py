"""Entry point for windcdf-qc."""

import sys


def main() -> int:
    """Main entry point."""
    from windcdf.gui.app import WindCDFApp

    app = WindCDFApp()
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
