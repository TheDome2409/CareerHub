from rich import print
from .job_sources import get_jobs


def startup():
    print("[green]Chevron sieben kodiert.[/green]")
    print("[cyan]JobAgent V0.1 gestartet[/cyan]")

    jobs = get_jobs()

    print("\nGefundene Stellen:")

    for job in jobs:
        print(f" - {job['title']} bei {job['company']} ({job['location']})")