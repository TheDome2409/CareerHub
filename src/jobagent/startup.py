import random

from rich import print

from jobagent.easter_eggs import STARTUP_MESSAGES
from jobagent.output_mode import (
    ask_output_mode,
    OutputMode,
)
from jobagent.services.job_service import (
    load_and_rank_jobs,
)


def startup():
    output_mode = ask_output_mode()

    if output_mode == OutputMode.ASGARD:
        print(
            f"[green]{random.choice(STARTUP_MESSAGES)}[/green]"
        )
        print(
            "[cyan]Asgard-Protokoll aktiviert[/cyan]"
        )
    else:
        print(
            "[cyan]CareerHub V0.1 gestartet[/cyan]"
        )

    ranked_jobs = load_and_rank_jobs(
        min_score=20
    )

    if not ranked_jobs:

        if output_mode == OutputMode.ASGARD:
            print(
                "\n[yellow]"
                "MALP meldet nur primitive Lebensformen."
                "[/yellow]"
            )
        else:
            print(
                "\n[yellow]"
                "Keine passenden Jobs gefunden."
                "[/yellow]"
            )

        return

    if output_mode == OutputMode.ASGARD:
        print("\nTop Missionen:\n")
    else:
        print("\nTop Jobs:\n")

    for result in ranked_jobs:

        job = result["job"]

        print(
            f"[bold]{job.title}[/bold] "
            f"bei {job.company}"
        )

        if job.career_tags:
            print(
                f"Tags: "
                f"{', '.join(job.career_tags)}"
            )

        print(
            f"Score: {result['score']}"
        )

        if output_mode == OutputMode.ASGARD:

            if result["score"] >= 100:
                print(
                    "[bold green]"
                    "ASCENSION PROTOCOL AVAILABLE"
                    "[/bold green]"
                )

            elif result["score"] >= 95:
                print(
                    "[bold red]"
                    "⚠ ANCIENT TECHNOLOGY DETECTED"
                    "[/bold red]"
                )

        for reason in result["reasons"]:

            if reason.startswith("  - "):
                print(
                    f"    ✓ "
                    f"{reason.replace('  - ', '')}"
                )
            else:
                print(
                    f"  + {reason}"
                )

        print()
