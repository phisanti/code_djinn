from djinn_sample.config import DEFAULT_REGION, RETRY_BUDGET
from djinn_sample.search import query_catalog


def build_status() -> dict[str, str]:
    return {
        "status": "ok",
        "region": DEFAULT_REGION,
    }


def startup_plan() -> list[str]:
    plan = ["load-config", "warm-cache"]
    if RETRY_BUDGET > 2:
        plan.append("enable-retry-monitor")
    return plan


def handle_query(term: str) -> list[str]:
    return query_catalog(term)
