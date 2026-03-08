"""Lógica de agregación y resumen de samples."""

from collections import defaultdict
from dataclasses import dataclass

from ztrace.exporter import TraceMetadata
from ztrace.parser import Sample


def summarize(
    samples: list[Sample],
    metadata: TraceMetadata | None = None,
    depth: int = 5,
    threshold: float = 1.0,
) -> str:
    """Genera un resumen compacto de los samples."""
    total_weight = sum(s.weight_ns for s in samples)
    if total_weight == 0:
        return "No samples found.\n"

    stats = _compute_stats(samples, depth)
    return _format(stats, total_weight, len(samples), metadata, depth, threshold)


@dataclass
class _Stats:
    # función → (self_weight, binary_name)
    self_time: dict[str, tuple[int, str]]
    # función → total_weight
    total_time: dict[str, int]
    # stack tuple → weight
    stack_weight: dict[tuple[str, ...], int]


def _compute_stats(samples: list[Sample], depth: int) -> _Stats:
    self_time: dict[str, tuple[int, str]] = {}
    total_time: dict[str, int] = defaultdict(int)
    stack_weight: dict[tuple[str, ...], int] = defaultdict(int)

    for sample in samples:
        user_frames = [f for f in sample.frames if f.is_user]
        if not user_frames:
            continue

        # Self time: frame de usuario más cercano al leaf
        leaf = user_frames[0]
        prev_w, prev_bin = self_time.get(leaf.name, (0, leaf.binary_name))
        self_time[leaf.name] = (prev_w + sample.weight_ns, prev_bin)

        # Total time
        seen: set[str] = set()
        for f in user_frames:
            if f.name not in seen:
                total_time[f.name] += sample.weight_ns
                seen.add(f.name)

        # Call stacks compactos
        stack_key = tuple(f.name for f in user_frames[:depth])
        stack_weight[stack_key] += sample.weight_ns

    return _Stats(
        self_time=self_time,
        total_time=total_time,
        stack_weight=stack_weight,
    )


def _format(
    stats: _Stats,
    total_weight: int,
    num_samples: int,
    metadata: TraceMetadata | None,
    depth: int,
    threshold: float,
) -> str:
    lines: list[str] = []

    # Header con metadata
    if metadata:
        lines.append(
            f"Process: {metadata.process_name}  "
            f"Duration: {metadata.duration_s:.1f}s  "
            f"Template: {metadata.template}"
        )
    total_ms = total_weight / 1_000_000
    lines.append(f"Samples: {num_samples}  Total CPU: {total_ms:.0f}ms")
    lines.append("")

    # Hotspots (self time) con módulo
    lines.append("SELF TIME")
    sorted_self = sorted(
        stats.self_time.items(), key=lambda x: x[1][0], reverse=True
    )
    for name, (weight, binary) in sorted_self:
        pct = 100 * weight / total_weight
        if pct < threshold:
            break
        ms = weight / 1_000_000
        lines.append(f"  {pct:5.1f}%  {ms:6.0f}ms  {binary}  {name}")

    # Total time — solo funciones cuyo total > self * 1.1
    callers = []
    for name, total_w in stats.total_time.items():
        self_w = stats.self_time.get(name, (0, ""))[0]
        if total_w > self_w * 1.1:
            pct = 100 * total_w / total_weight
            if pct >= threshold:
                callers.append((name, total_w))
    if callers:
        lines.append("")
        lines.append("TOTAL TIME (callers with significant overhead)")
        callers.sort(key=lambda x: x[1], reverse=True)
        for name, weight in callers:
            pct = 100 * weight / total_weight
            ms = weight / 1_000_000
            lines.append(f"  {pct:5.1f}%  {ms:6.0f}ms  {name}")

    # Call stacks compactos: root > child > leaf
    lines.append("")
    lines.append("CALL STACKS")
    sorted_stacks = sorted(
        stats.stack_weight.items(), key=lambda x: x[1], reverse=True
    )
    for stack, weight in sorted_stacks[:10]:
        pct = 100 * weight / total_weight
        if pct < threshold:
            break
        ms = weight / 1_000_000
        # Invertir: mostrar root > ... > leaf (más natural para leer)
        chain = " > ".join(reversed(stack))
        lines.append(f"  {pct:5.1f}%  {ms:6.0f}ms  {chain}")

    lines.append("")
    return "\n".join(lines)
