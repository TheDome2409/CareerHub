from __future__ import annotations

import argparse

from openllmbench.evaluators.human.reviewer import create_blank_review, next_review_candidate
from openllmbench.evaluators.human.review_writer import save_review
from openllmbench.sdk.cli import add_create_suite_parser


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenLLMBench Foundation CLI")
    subparsers = parser.add_subparsers(dest="command")
    review = subparsers.add_parser("review", help="Find the next unreviewed benchmark task.")
    review.add_argument("--run-id", required=True)
    review.add_argument("--outputs-dir", default="benchmarks/outputs")
    review.add_argument("--reviews-dir", default="reviews")
    review.add_argument("--rubric", default="evaluation_profiles/careerhub.yaml")
    review.add_argument("--reviewer", default="human")
    review.add_argument("--create", action="store_true", help="Create a blank YAML review file.")
    add_create_suite_parser(subparsers)
    args = parser.parse_args()

    if hasattr(args, "func"):
        args.func(args)
        return

    if args.command == "review":
        _review(args)
        return

    print(
        "OpenLLMBench Foundation V1\n"
        "No runtime benchmark CLI is implemented yet. "
        "Use `python -m careerhub.benchmark_runner` for existing benchmarks."
    )


def _review(args: argparse.Namespace) -> None:
    candidate = next_review_candidate(
        run_id=args.run_id,
        outputs_dir=args.outputs_dir,
        reviews_dir=args.reviews_dir,
    )
    if candidate is None:
        print(f"No unreviewed task found for run `{args.run_id}`.")
        return
    print("Next unreviewed task:")
    print(f"- run_id: {candidate['run_id']}")
    print(f"- model: {candidate['model']}")
    print(f"- task: {candidate['task']}")
    print(f"- task_file: {candidate['task_file']}")
    print(f"- review_file: {candidate['review_file']}")
    if args.create:
        scorecard = create_blank_review(
            rubric_path=args.rubric,
            run_id=candidate["run_id"],
            model=candidate["model"],
            task=candidate["task"],
            reviewer=args.reviewer,
        )
        path = save_review(scorecard, candidate["review_file"])
        print(f"Created blank review: {path}")


if __name__ == "__main__":
    main()
