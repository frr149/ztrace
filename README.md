# ztrace

Compact `xctrace` (Instruments) summaries optimized for LLM consumption.

**33,000 lines of XML → 10 actionable lines.**

## Problem

`xctrace export` generates exhaustive XML — every sample, every backtrace frame, every memory address. This is great for Instruments' interactive UI, but when an LLM needs to find hotspots, the signal-to-noise ratio is brutal.

## Example

```
$ ztrace summary ./MyApp.trace

Process: ghostty  Duration: 3.8s  Template: Time Profiler
Samples: 295  Total CPU: 295ms

SELF TIME
   53.2%     157ms  ghostty  main
    3.7%      11ms  ghostty  renderer.metal.RenderPass.begin
    3.1%       9ms  ghostty  renderer.generic.Renderer(renderer.Metal).rebuildCells
    2.7%       8ms  ghostty  renderer.generic.Renderer(renderer.Metal).drawFrame
    1.7%       5ms  ghostty  font.shaper.coretext.Shaper.shape

CALL STACKS
   53.2%     157ms  main
    1.7%       5ms  main > @objc TerminalWindow.title.setter
```

## What it does

1. Runs `xctrace export --toc` for trace metadata (process, duration, template)
2. Runs `xctrace export --xpath` to extract the `time-profile` table
3. Parses the XML, resolving xctrace's `id`/`ref` deduplication system
4. Filters non-actionable frames (system libraries, Swift runtime internals, dyld stubs, unsymbolicated addresses)
5. Aggregates by function with self time, total time, and call stacks

## Install

```bash
# With uv (recommended)
uv tool install git+https://github.com/frr149/ztrace

# From source
git clone https://github.com/frr149/ztrace
cd ztrace
uv sync
```

## Usage

```bash
# Summarize a .trace bundle
ztrace summary ./MyApp.trace

# Lower threshold to show more functions (default: 1%)
ztrace summary ./MyApp.trace --threshold 0.5

# Deeper call stacks (default: 5)
ztrace summary ./MyApp.trace --depth 10
```

## What gets filtered

| Category | Examples | Why |
|----------|----------|-----|
| System libraries | libdispatch, dyld, libsystem_m | Can't optimize what you don't own |
| Swift/ObjC runtime | `__swift_instantiate*`, `_swift_*` | Runtime internals, not your code |
| Dyld stubs | `DYLD-STUB$$sin` | Dynamic linker thunks |
| Unsymbolicated frames | `0x104885404` | Stripped binaries — noted in output |

When a binary is stripped (e.g. Spotify), ztrace reports the percentage of unsymbolicated samples so you know you need dSYMs for a full picture.

## Requirements

- macOS (xctrace is Apple-only)
- Python ≥ 3.12
- Xcode Command Line Tools (`xcode-select --install`)

## License

MIT
