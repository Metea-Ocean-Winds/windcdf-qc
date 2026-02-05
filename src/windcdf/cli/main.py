"""Command-line interface for windcdf-qc."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="windcdf",
        description="Time series QC tool for wind measurement NetCDF files",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # QC command
    qc_parser = subparsers.add_parser("qc", help="Run QC checks")
    qc_parser.add_argument("input", help="Input NetCDF file")
    qc_parser.add_argument(
        "-o", "--out",
        help="Output report file (JSON)",
    )
    qc_parser.add_argument(
        "-c", "--config",
        help="Custom config file",
    )
    qc_parser.add_argument(
        "--checks",
        help="Comma-separated list of checks to run",
    )
    qc_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    # Export command
    export_parser = subparsers.add_parser("export", help="Export data")
    export_parser.add_argument("input", help="Input NetCDF file")
    export_parser.add_argument(
        "-f", "--format",
        choices=["csv", "json"],
        default="json",
        help="Output format",
    )
    export_parser.add_argument(
        "-o", "--out",
        help="Output file path",
    )

    # GUI command (default)
    subparsers.add_parser("gui", help="Launch GUI")

    return parser


def run_qc(args: argparse.Namespace) -> int:
    """Run QC command."""
    from windcdf.io.reader import NetCDFReader
    from windcdf.io.writer import NetCDFWriter
    from windcdf.qc.engine import QCEngine

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"Loading {input_path}...")

    reader = NetCDFReader(input_path)
    dataset = reader.open()

    if args.verbose:
        print(f"Found variables: {list(dataset.data_vars)}")

    # Run QC
    engine = QCEngine()
    checks = args.checks.split(",") if args.checks else None
    report = engine.run(dataset, checks=checks)

    if args.verbose:
        print(f"QC complete. Found {report.total_flags} flags.")
        for severity, count in report.flags_by_severity.items():
            print(f"  {severity}: {count}")

    # Save report
    if args.out:
        writer = NetCDFWriter(args.out)
        writer.export_report_json(report, args.out)
        print(f"Report saved to {args.out}")

    reader.close()
    return 0


def run_export(args: argparse.Namespace) -> int:
    """Run export command."""
    print("Export functionality coming soon")
    return 0


def run_gui(args: argparse.Namespace) -> int:
    """Launch GUI."""
    from windcdf.gui.app import WindCDFApp

    app = WindCDFApp()
    app.run()
    return 0


def cli(argv: list[str] | None = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None or args.command == "gui":
        return run_gui(args)
    elif args.command == "qc":
        return run_qc(args)
    elif args.command == "export":
        return run_export(args)
    else:
        parser.print_help()
        return 1


def main() -> None:
    """Entry point for console script."""
    sys.exit(cli())


if __name__ == "__main__":
    main()
