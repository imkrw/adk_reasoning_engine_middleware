import os

PROJECT = os.getenv("PROJECT")
LOCATION = os.getenv("LOCATION")
DEFAULT_REASONING_ID = os.getenv("REASONING_ID")

# 3 hours TTL for user session (in seconds = 3 * 60 * 60)
SESSION_TTL_SECONDS = 3 * 60 * 60

CONTACT_STAFF_MSG = "Human assistance requested."


def get_reasoning_id() -> str:
    if not DEFAULT_REASONING_ID:
        raise RuntimeError("REASONING_ID is not configured in environment variables")
    return DEFAULT_REASONING_ID


def _build_base_url(reasoning_id: str) -> str:
    return (
        f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}"
        f"/locations/{LOCATION}/reasoningEngines/{reasoning_id}"
    )


def get_query_url() -> str:
    rid = get_reasoning_id()
    return f"{_build_base_url(rid)}:query"


def get_stream_url() -> str:
    rid = get_reasoning_id()
    return f"{_build_base_url(rid)}:streamQuery?alt=sse"
