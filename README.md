# ztrace

CLI tool that summarizes `xctrace` (Instruments) output into a compact format optimized for LLM consumption (especially Claude Code).

## Problem

`xctrace export` generates XML files with tens of thousands of lines — full call trees, individual samples, repetitive metadata. When Claude Code profiles Swift apps with xctrace, this output quickly consumes the context window and buries actionable information in noise.

## What ztrace does

Takes a `.trace` bundle (or records one) and produces a ~200-line summary with real hotspots, filtering out non-actionable system frames.

## Planned usage

```bash
# Summarize an existing .trace
ztrace summary ./MyApp.trace

# Record + summarize in one step
ztrace record ./MyApp --template 'Time Profiler' --duration 5
```

## Output goals

- Compact: fits in <200 lines for a typical trace
- Actionable: shows user code hotspots with CPU % attribution
- LLM-friendly: no decorative formatting, just structured information
- Filtered: excludes system frames (UIKit internals, libdispatch, etc.)

## Stack

- **Language:** Swift
- **Build:** Swift Package Manager
- **Dependencies:** minimal — Foundation XMLParser for XML processing
- **Tests:** XCTest with real trace fixtures

## Status

Early development — currently in Phase 0 (researching xctrace export format with real data before writing any parsing code).

## License

MIT
