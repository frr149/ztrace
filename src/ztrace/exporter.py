"""Wrapper sobre xctrace export."""

import subprocess
import sys
from dataclasses import dataclass

import xml.etree.ElementTree as ET


XPATH_TIME_PROFILE = (
    '/trace-toc/run[@number="1"]/data/table[@schema="time-profile"]'
)


@dataclass
class TraceMetadata:
    process_name: str
    duration_s: float
    template: str


def export_toc(trace_path: str) -> str:
    """Exporta la tabla de contenidos del trace."""
    return _run_xctrace(["--input", trace_path, "--toc"])


def export_time_profile(trace_path: str) -> str:
    """Exporta la tabla time-profile del trace."""
    return _run_xctrace(["--input", trace_path, "--xpath", XPATH_TIME_PROFILE])


def parse_metadata(toc_xml: str) -> TraceMetadata:
    """Extrae metadata del TOC XML."""
    root = ET.fromstring(toc_xml)
    run = root.find(".//run")

    process_name = ""
    process_el = run.find(".//info/target/process") if run is not None else None
    if process_el is not None:
        process_name = process_el.get("name", "")

    duration_s = 0.0
    duration_el = run.find(".//summary/duration") if run is not None else None
    if duration_el is not None and duration_el.text:
        duration_s = float(duration_el.text)

    template = ""
    template_el = run.find(".//summary/template-name") if run is not None else None
    if template_el is not None and template_el.text:
        template = template_el.text

    return TraceMetadata(
        process_name=process_name,
        duration_s=duration_s,
        template=template,
    )


def _run_xctrace(args: list[str]) -> str:
    result = subprocess.run(
        ["xctrace", "export", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Error: xctrace export failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout
