from typing import Any, Dict, List

import pandas as pd

from app.engine.nodes.base_node import BaseNode, register_node


def parse_variables(raw: Any) -> List[Dict[str, str]]:
    """Dipakai node & python generator agar logikanya identik (DRY)."""
    items: List[Dict[str, str]] = []
    if isinstance(raw, dict):
        return [{"key": str(k), "value": str(v)} for k, v in raw.items()]
    for chunk in str(raw or "").replace("\n", ",").split(","):
        if "=" in chunk:
            key, value = chunk.split("=", 1)
            if key.strip():
                items.append({"key": key.strip(), "value": value.strip()})
    return items


@register_node("manual_variable")
class ManualVariableNode(BaseNode):
    title = "Manual Variable"
    category = "sources"
    description = "Menghasilkan tabel key/value untuk parameter node downstream."
    max_inputs = 0
    config_schema = [
        {"name": "variables", "label": "Variabel (key=value, pisahkan koma)",
         "type": "textarea", "default": "status_order=Lunas, min_total=500000"},
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        rows = parse_variables(self.config.get("variables"))
        return pd.DataFrame(rows, columns=["key", "value"])
