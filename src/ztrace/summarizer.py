"""Lógica de agregación y resumen de samples."""

from collections import defaultdict

from ztrace.parser import Sample


def summarize(
    samples: list[Sample],
    depth: int = 5,
    threshold: float = 1.0,
) -> str:
    """Genera un resumen compacto de los samples.

    Args:
        samples: Lista de samples parseados.
        depth: Profundidad máxima del call stack a mostrar.
        threshold: Porcentaje mínimo para incluir una función.
    """
    total_weight = sum(s.weight_ns for s in samples)
    if total_weight == 0:
        return "No samples found.\n"

    # Acumular peso por función de usuario (self time)
    self_time: dict[str, int] = defaultdict(int)
    # Acumular peso por función de usuario (total time — aparece en el stack)
    total_time: dict[str, int] = defaultdict(int)
    # Guardar call stacks de usuario más frecuentes
    stack_weight: dict[tuple[str, ...], int] = defaultdict(int)

    for sample in samples:
        user_frames = [f for f in sample.frames if f.is_user]
        if not user_frames:
            continue

        # Self time: la función de usuario más cercana al leaf
        self_time[user_frames[0].name] += sample.weight_ns

        # Total time: cada función de usuario en el stack
        seen: set[str] = set()
        for f in user_frames:
            if f.name not in seen:
                total_time[f.name] += sample.weight_ns
                seen.add(f.name)

        # Call stack de usuario (limitado a depth)
        stack_key = tuple(f.name for f in user_frames[:depth])
        stack_weight[stack_key] += sample.weight_ns

    # Formatear output
    lines: list[str] = []
    total_ms = total_weight / 1_000_000

    lines.append(f"Total: {total_ms:.0f}ms ({len(samples)} samples)\n")

    # Hotspots por self time
    lines.append("── Hotspots (self time) ──\n")
    sorted_self = sorted(self_time.items(), key=lambda x: x[1], reverse=True)
    for name, weight in sorted_self:
        pct = 100 * weight / total_weight
        if pct < threshold:
            break
        ms = weight / 1_000_000
        lines.append(f"  {pct:5.1f}%  {ms:7.0f}ms  {name}\n")

    # Hotspots por total time (si difiere del self time)
    if _has_nontrivial_callers(sorted_self, total_time, total_weight, threshold):
        lines.append("\n── Hotspots (total time) ──\n")
        sorted_total = sorted(total_time.items(), key=lambda x: x[1], reverse=True)
        for name, weight in sorted_total:
            pct = 100 * weight / total_weight
            if pct < threshold:
                break
            ms = weight / 1_000_000
            lines.append(f"  {pct:5.1f}%  {ms:7.0f}ms  {name}\n")

    # Top call stacks
    lines.append("\n── Top call stacks ──\n")
    sorted_stacks = sorted(stack_weight.items(), key=lambda x: x[1], reverse=True)
    for stack, weight in sorted_stacks[:10]:
        pct = 100 * weight / total_weight
        if pct < threshold:
            break
        ms = weight / 1_000_000
        lines.append(f"  {pct:5.1f}%  {ms:7.0f}ms\n")
        for i, fname in enumerate(stack):
            prefix = "    → " if i == 0 else "      "
            lines.append(f"{prefix}{fname}\n")

    return "".join(lines)


def _has_nontrivial_callers(
    sorted_self: list[tuple[str, int]],
    total_time: dict[str, int],
    total_weight: int,
    threshold: float,
) -> bool:
    """True si hay funciones cuyo total time difiere significativamente del self time."""
    for name, self_w in sorted_self:
        total_w = total_time.get(name, self_w)
        if total_w > self_w * 1.1:  # >10% más en total que en self
            pct = 100 * total_w / total_weight
            if pct >= threshold:
                return True
    return False
