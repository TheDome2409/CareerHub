from __future__ import annotations

import argparse
from pathlib import Path

from openllmbench.sdk.builders import BenchmarkSuiteBuilder


def add_create_suite_parser(subparsers) -> None:
    parser = subparsers.add_parser("create-suite", help="Scaffold a benchmark suite dataset.")
    parser.add_argument("name", help="Human-readable suite name.")
    parser.add_argument("--output-root", default="datasets")
    parser.add_argument("--description")
    parser.add_argument("--capabilities", nargs="*", default=["analysis", "reasoning"])
    parser.add_argument("--author", default="OpenLLMBench")
    parser.add_argument("--evaluation-profile")
    parser.set_defaults(func=run_create_suite)


def run_create_suite(args: argparse.Namespace) -> None:
    builder = BenchmarkSuiteBuilder(
        suite_name=args.name,
        output_root=Path(args.output_root),
        description=args.description,
        capabilities=args.capabilities,
        author=args.author,
        evaluation_profile=args.evaluation_profile,
    )
    paths = builder.build()
    print("Created OpenLLMBench suite scaffold:")
    for key, path in paths.items():
        print(f"- {key}: {path}")

