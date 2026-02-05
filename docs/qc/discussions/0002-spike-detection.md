# ADR 0002: Spike Detection

## Status
Accepted

## Context
Need to identify sudden unrealistic jumps in time series.

## Decision
Use a sliding window with configurable threshold multiplier.

## Consequences
- Effective for isolated spikes
- Window size affects sensitivity
