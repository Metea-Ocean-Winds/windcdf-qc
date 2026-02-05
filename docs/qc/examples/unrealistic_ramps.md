# Unrealistic Ramps Example

## Scenario

Wind speed changes too rapidly to be physically plausible.

## Detection

The ramp_rate check flags excessive rates of change.

## Typical Thresholds

- Wind speed: max 5 m/s per 10-minute interval
- Temperature: max 5°C per hour
