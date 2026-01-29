from pathlib import Path
from typing import Optional
import json
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    message: str


class HealthService:
    _data_path = Path(__file__).resolve().parent.parent / "data" / "store.json"

    @classmethod
    def check_health(cls) -> HealthResponse:
        status, message = cls._verify_static_dataset()
        overall = "healthy" if status == "static-json" else "unhealthy"
        return HealthResponse(status=overall, database=status, message=message)

    @classmethod
    def _verify_static_dataset(cls) -> tuple[str, str]:
        try:
            with cls._data_path.open("r", encoding="utf-8") as handle:
                json.load(handle)
            return "static-json", "Static dataset loaded successfully"
        except FileNotFoundError:
            return "missing", "Static dataset not found"
        except json.JSONDecodeError:
            return "invalid", "Static dataset is malformed"