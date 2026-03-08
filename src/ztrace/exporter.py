"""Wrapper sobre xctrace export."""

import subprocess
import sys


XPATH_TIME_PROFILE = (
    '/trace-toc/run[@number="1"]/data/table[@schema="time-profile"]'
)


def export_trace(trace_path: str) -> str:
    """Ejecuta xctrace export y devuelve el XML crudo."""
    result = subprocess.run(
        [
            "xctrace", "export",
            "--input", trace_path,
            "--xpath", XPATH_TIME_PROFILE,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error: xctrace export failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout
