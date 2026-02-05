"""Export QC flags to CSV format."""

from pathlib import Path
from windcdf.io.reader import NetCDFReader
from windcdf.qc.engine import QCEngine


def export_flags_csv(input_file: str, output_file: str) -> None:
    """Export QC flags from a NetCDF file to CSV.

    Args:
        input_file: Path to input NetCDF file.
        output_file: Path to output CSV file.
    """
    reader = NetCDFReader(input_file)
    dataset = reader.open()

    engine = QCEngine()
    report = engine.run(dataset)

    # Create CSV content
    lines = ["timestamp,variable,severity,check,message"]
    for flag in report.flags:
        timestamp = flag.timestamp.isoformat() if flag.timestamp else ""
        lines.append(
            f"{timestamp},{flag.variable},{flag.severity.name},"
            f"{flag.check_name},{flag.message}"
        )

    # Write CSV
    with open(output_file, "w") as f:
        f.write("\n".join(lines))

    print(f"Exported {len(report.flags)} flags to {output_file}")
    reader.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python export_flags_csv.py <input.nc> <output.csv>")
        sys.exit(1)

    export_flags_csv(sys.argv[1], sys.argv[2])
