from djinn_sample.search import CATALOG


def build_summary() -> dict[str, int]:
    return {
        "catalog_size": len(CATALOG),
        "zeta_index": 7,
    }


def render_summary() -> str:
    summary = build_summary()
    return f"{summary['catalog_size']} artifacts; zeta={summary['zeta_index']}"
