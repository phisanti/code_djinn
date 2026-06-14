DEFAULT_REGION = "eu-central-1"
API_TOKEN_NAME = "NEBULA_TOKEN"
RETRY_BUDGET = 3
MAX_BATCH_SIZE = 25


def token_help() -> str:
    return f"Set {API_TOKEN_NAME} before running maintenance scripts."
