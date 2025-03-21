import json


def load_dict(json_str: str) -> dict:
    """Load a json string into a dictionary."""
    assert isinstance(json_str, str), f"Expected str, got {type(json_str)}"
    out = json.loads(json_str)
    assert isinstance(out, dict)
    return out


def dump(data: dict | list) -> str:
    """Save a dictionary to a json string."""
    assert isinstance(data, dict) or isinstance(
        data, list
    ), f"Expected dict or list, got {type(data)}"
    out = json.dumps(data, indent=2)
    assert isinstance(out, str)
    return out
