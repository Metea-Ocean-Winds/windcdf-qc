"""Batch QC processing example."""

from pathlib import Path
from windcdf.io.reader import NetCDFReader
from windcdf.io.writer import NetCDFWriter
from windcdf.qc.engine import QCEngine


def run_batch_qc(input_dir: str, output_dir: str) -> None:
    """Run QC on all NetCDF files in a directory.

    Args:
        input_dir: Directory with input files.
        output_dir: Directory for output reports.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    engine = QCEngine()

    for nc_file in input_path.glob("*.nc"):
        print(f"Processing {nc_file.name}...")

        reader = NetCDFReader(nc_file)
        dataset = reader.open()

        report = engine.run(dataset)
        print(f"  Found {report.total_flags} flags")

        # Save report
        report_path = output_path / f"{nc_file.stem}_qc_report.json"
        writer = NetCDFWriter(report_path)
        writer.export_report_json(report, report_path)

        reader.close()

    print("Batch processing complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python run_qc_batch.py <input_dir> <output_dir>")
        sys.exit(1)

    run_batch_qc(sys.argv[1], sys.argv[2])
