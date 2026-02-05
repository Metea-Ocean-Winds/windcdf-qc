"""Benchmark QC engine performance."""

import time
import numpy as np
import xarray as xr

from windcdf.qc.engine import QCEngine


def create_large_dataset(n_points: int) -> xr.Dataset:
    """Create a large test dataset.

    Args:
        n_points: Number of time points.

    Returns:
        xarray Dataset.
    """
    time = np.arange(
        "2020-01-01",
        np.datetime64("2020-01-01") + np.timedelta64(n_points, "h"),
        dtype="datetime64[h]",
    )
    wind_speed = np.random.uniform(0, 25, n_points)
    wind_direction = np.random.uniform(0, 360, n_points)
    temperature = np.random.uniform(-10, 35, n_points)

    return xr.Dataset(
        {
            "wind_speed": (["time"], wind_speed),
            "wind_direction": (["time"], wind_direction),
            "temperature": (["time"], temperature),
        },
        coords={"time": time},
    )


def benchmark_engine(n_points: int, n_runs: int = 5) -> dict:
    """Benchmark QC engine.

    Args:
        n_points: Number of data points.
        n_runs: Number of runs for averaging.

    Returns:
        Benchmark results.
    """
    dataset = create_large_dataset(n_points)
    engine = QCEngine()

    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        report = engine.run(dataset)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return {
        "n_points": n_points,
        "n_runs": n_runs,
        "mean_time": np.mean(times),
        "std_time": np.std(times),
        "min_time": np.min(times),
        "max_time": np.max(times),
        "total_flags": report.total_flags,
    }


def main() -> None:
    """Run benchmarks."""
    sizes = [1000, 10000, 100000, 1000000]

    print("windcdf-qc Engine Benchmark")
    print("=" * 50)

    for size in sizes:
        print(f"\nBenchmarking {size:,} data points...")
        results = benchmark_engine(size)
        print(f"  Mean time: {results['mean_time']:.3f}s (±{results['std_time']:.3f}s)")
        print(f"  Flags found: {results['total_flags']}")
        print(f"  Throughput: {size / results['mean_time']:,.0f} points/sec")


if __name__ == "__main__":
    main()
