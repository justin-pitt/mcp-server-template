import json
from typing import Any


def create_response(*, data: Any | None = None, error: str | None = None) -> str:
    """Wrap a tool response in a consistent envelope.

    Args:
        data: Successful response payload.
        error: Error message; mutually exclusive with data.

    Returns:
        JSON-encoded string. On error, includes {"error": ...} key.
    """
    if error is not None:
        return json.dumps({"error": error})
    return json.dumps({"data": data})
