# ADR 0004: Wind Direction Wrap

## Status
Accepted

## Context
Wind direction wraps at 0°/360°, causing false spike detection.

## Decision
Use circular statistics for direction-based checks.

## Consequences
- Requires special handling in spike and ramp checks
- More accurate flagging for direction variables
