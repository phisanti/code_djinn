CATALOG = {
    "artifact-17": "old bronze astrolabe",
    "artifact-42": "glass compass with blue rim",
    "artifact-99": "sealed crate marked NOVA-HARBOUR",
}


def query_catalog(term: str) -> list[str]:
    needle = term.lower()
    return [
        artifact_id
        for artifact_id, description in CATALOG.items()
        if needle in description.lower()
    ]
