"""Punto de entrada CLI de ztrace."""

import argparse
import sys

from ztrace.exporter import export_trace
from ztrace.parser import parse_time_profile
from ztrace.summarizer import summarize


def main() -> None:
    args = parse_args()
    args.func(args)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ztrace",
        description="Compact xctrace summaries for LLMs",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ztrace summary <trace-file>
    sp = sub.add_parser("summary", help="Summarize a .trace file")
    sp.add_argument("trace", help="Path to .trace bundle")
    sp.add_argument(
        "--depth",
        type=int,
        default=5,
        help="Max call stack depth to show (default: 5)",
    )
    sp.add_argument(
        "--threshold",
        type=float,
        default=1.0,
        help="Min %% of total time to include a function (default: 1.0)",
    )
    sp.set_defaults(func=cmd_summary)

    return parser.parse_args()


def cmd_summary(args: argparse.Namespace) -> None:
    """Exporta, parsea y resume un .trace."""
    xml_data = export_trace(args.trace)
    samples = parse_time_profile(xml_data)
    output = summarize(samples, depth=args.depth, threshold=args.threshold)
    sys.stdout.write(output)
