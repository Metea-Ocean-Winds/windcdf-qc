# CLI Reference

## Commands

### `windcdf qc`

Run QC checks on a NetCDF file.

```bash
windcdf qc <input.nc> [OPTIONS]

Options:
  --out, -o      Output report file (JSON)
  --config, -c   Custom config file
  --checks       Comma-separated list of checks to run
  --verbose, -v  Verbose output
```

### `windcdf export`

Export flagged data or cleaned datasets.

```bash
windcdf export <input.nc> --format csv
```
