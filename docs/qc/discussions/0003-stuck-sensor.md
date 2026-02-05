# ADR 0003: Stuck Sensor

## Status
Accepted

## Context
Sensors can freeze or fail, reporting constant values.

## Decision
Flag sequences of identical values exceeding a duration threshold.

## Consequences
- Works well for icing conditions
- May false-positive on calm conditions (need wind speed context)
