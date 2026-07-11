from enum import Enum


class OutputMode(str, Enum):
    HUMAN = "human"
    ASGARD = "asgard"


def ask_output_mode() -> OutputMode:
    print("Ausgabemodus wählen:")
    print("1 = Mensch")
    print("2 = Asgard")

    choice = input("> ").strip()

    if choice == "2":
        return OutputMode.ASGARD

    return OutputMode.HUMAN