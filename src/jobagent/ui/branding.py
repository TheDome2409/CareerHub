import base64
from pathlib import Path


APP_NAME = "CareerHub"
LOGO_PATH = (
    Path(__file__).parent
    / "assets"
    / "careerhub-logo.svg"
)


def logo_data_uri() -> str:
    data = LOGO_PATH.read_bytes()
    encoded = base64.b64encode(data).decode("ascii")

    return f"data:image/svg+xml;base64,{encoded}"
