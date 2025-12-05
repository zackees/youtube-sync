import json5


def load_dict(json_str: str) -> dict:
    """Load a JSON5 string into a dictionary. Supports comments and trailing commas."""
    assert isinstance(json_str, str), f"Expected str, got {type(json_str)}"
    out = json5.loads(json_str)
    assert isinstance(out, dict)
    return out


def dump(data: dict | list) -> str:
    """Save a dictionary to a JSON5 string."""
    assert isinstance(data, dict) or isinstance(
        data, list
    ), f"Expected dict or list, got {type(data)}"
    out = json5.dumps(data, indent=2)
    assert isinstance(out, str)
    return out
