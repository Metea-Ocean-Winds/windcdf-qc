# Architecture

## Overview

windcdf-qc follows a modular architecture separating concerns:

```
┌─────────────────────────────────────────┐
│                  GUI                     │
│   (Tkinter views, controllers, state)   │
├─────────────────────────────────────────┤
│              QC Engine                   │
│   (checks registry, pipeline, scoring)  │
├─────────────────────────────────────────┤
│               Models                     │
│   (flags, reports, time series)         │
├─────────────────────────────────────────┤
│                 I/O                      │
│   (NetCDF reader/writer, conventions)   │
└─────────────────────────────────────────┘
```

## Key Design Decisions

- MVC pattern for GUI
- Plugin-style check registration
- Configuration-driven thresholds
