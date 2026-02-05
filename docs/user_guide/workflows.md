# Workflows

## Standard QC Workflow

1. Load NetCDF file
2. Run automatic QC pipeline
3. Review flagged points
4. Accept/reject flags
5. Export report

## Batch Processing

Use the CLI for processing multiple files:

```bash
for f in data/*.nc; do
    windcdf qc "$f" --out "reports/$(basename $f .nc).json"
done
```
