"""Base node + registry plugin otomatis."""
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type

import pandas as pd

NODE_REGISTRY: Dict[str, Type["BaseNode"]] = {}


class NodeExecutionError(Exception):
    """Error fungsional node dengan pesan ramah pengguna."""


def register_node(node_type: str) -> Callable[[Type["BaseNode"]], Type["BaseNode"]]:
    def decorator(cls: Type["BaseNode"]) -> Type["BaseNode"]:
        if node_type in NODE_REGISTRY and NODE_REGISTRY[node_type] is not cls:
            raise RuntimeError("Node type duplikat: {}".format(node_type))
        cls.node_type = node_type
        NODE_REGISTRY[node_type] = cls
        return cls
    return decorator


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def split_columns(raw: Any) -> List[str]:
    if isinstance(raw, (list, tuple)):
        return [str(c).strip() for c in raw if str(c).strip()]
    return [c.strip() for c in str(raw or "").split(",") if c.strip()]


class BaseNode(ABC):
    node_type: str = "base"
    title: str = "Base Node"
    category: str = "transforms"
    description: str = ""
    config_schema: List[Dict[str, Any]] = []
    min_inputs: int = 0
    max_inputs: Optional[int] = None

    def __init__(self, node_id: str, config: Optional[Dict[str, Any]] = None):
        self.node_id = node_id
        self.config = config or {}
        self.artifacts: List[Dict[str, str]] = []

    def cfg(self, key: str, default: Any = None) -> Any:
        value = self.config.get(key, default)
        return default if value is None or value == "" else value

    @abstractmethod
    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        raise NotImplementedError

    @classmethod
    def spec(cls) -> Dict[str, Any]:
        return {
            "type": cls.node_type,
            "title": cls.title,
            "category": cls.category,
            "description": cls.description,
            "minInputs": cls.min_inputs,
            "maxInputs": cls.max_inputs,
            "config_schema": cls.config_schema,
        }

    # ---- helper untuk subclass ----
    @staticmethod
    def require_columns(df: pd.DataFrame, columns: List[str]) -> None:
        missing = [c for c in columns if c not in df.columns]
        if missing:
            raise NodeExecutionError(
                "Kolom {} tidak ditemukan. Kolom tersedia: {}".format(missing, list(df.columns))
            )
