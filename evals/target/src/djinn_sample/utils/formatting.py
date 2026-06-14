CALYPSO_MARKER = "calypso-marker"


def normalize_title(value: str) -> str:
    return " ".join(value.strip().split()).title()


def marker_label() -> str:
    return f"marker:{CALYPSO_MARKER}"
