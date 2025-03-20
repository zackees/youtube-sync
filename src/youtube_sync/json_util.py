import json


def load_dict(json_str: str) -> dict:
    """Load a json string into a dictionary."""
    out = json.loads(json_str)
    assert isinstance(out, dict)
    return out


def dump(data: dict | list) -> str:
    """Save a dictionary to a json string."""
    out = json.dumps(data, indent=2)
    assert isinstance(out, str)
    return out
