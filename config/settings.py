import os

PROJECT = os.getenv("PROJECT")
LOCATION = os.getenv("LOCATION")
DEFAULT_REASONING_ID = os.getenv("REASONING_ID")

REASONING_ID_MAP: dict[str, str] = {
    "01979976-d037-7dea-9a44-50fe9042e780": "REASONING_ID_F",
    "41818654-1191-42c5-8955-038f57e62106": "REASONING_ID_A",
}

# 3 hours TTL for user session (in seconds = 3 * 60 * 60)
SESSION_TTL_SECONDS = 3 * 60 * 60

CONTACT_STAFF_MSG = "Human assistance requested."


def get_reasoning_id(company_id: str | None) -> str:
    if not company_id:
        if not DEFAULT_REASONING_ID:
            raise RuntimeError(
                "REASONING_ID is not configured in environment variables"
            )
        return DEFAULT_REASONING_ID

    env_key = REASONING_ID_MAP.get(company_id)
    if env_key:
        reasoning_id = os.getenv(env_key)
        if reasoning_id:
            return reasoning_id

    if not DEFAULT_REASONING_ID:
        raise RuntimeError("REASONING_ID is not configured in environment variables")
    return DEFAULT_REASONING_ID


def _build_base_url(reasoning_id: str) -> str:
    return (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}"
        f"/locations/{LOCATION}/reasoningEngines/{reasoning_id}"
    )


def get_query_url(company_id: str | None) -> str:
    # get query URL based on company_id
    rid = get_reasoning_id(company_id)
    return f"{_build_base_url(rid)}:query"


def get_stream_url(company_id: str | None) -> str:
    rid = get_reasoning_id(company_id)
    return f"{_build_base_url(rid)}:streamQuery?alt=sse"
