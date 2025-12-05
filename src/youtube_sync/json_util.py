from typing import Any

import json5


def load_dict(json_str: str) -> dict[str, Any]:
    """Load a JSON5 string into a dictionary. Supports comments and trailing commas."""
    assert isinstance(json_str, str), f"Expected str, got {type(json_str)}"
    out = json5.loads(json_str)  # type: ignore[reportUnknownVariableType]
    assert isinstance(out, dict)
    return out  # type: ignore[reportUnknownVariableType]


def dump(data: dict[str, Any] | list[Any]) -> str:
    """Save a dictionary to a JSON5 string."""
    assert isinstance(data, dict) or isinstance(
        data, list
    ), f"Expected dict or list, got {type(data)}"
    out = json5.dumps(data, indent=2)  # type: ignore[reportUnknownMemberType]
    assert isinstance(out, str)
    return out
