from pathlib import Path
from typing import Any, Dict
import json


_DATA_PATH = Path(__file__).resolve().parent / "data" / "store.json"


def load_static_data() -> Dict[str, Any]:
    with _DATA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_connection() -> bool:
    try:
        load_static_data()
        return True
    except (FileNotFoundError, json.JSONDecodeError):
        return False