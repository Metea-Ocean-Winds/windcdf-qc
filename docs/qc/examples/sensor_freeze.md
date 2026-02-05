# Sensor Freeze Example

## Scenario

Anemometer frozen due to icing, reporting constant values.

## Detection

The stuck_sensor check identifies repeated identical values.

## Thresholds

- Minimum stuck duration: 6 timestamps
- Tolerance: 0.001 (for floating point comparison)
