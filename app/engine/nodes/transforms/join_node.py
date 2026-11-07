from typing import List

import pandas as pd

from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node, split_columns


@register_node("join_node")
class JoinNode(BaseNode):
    title = "Join"
    category = "transforms"
    description = "Menggabungkan 2 tabel. Port IN 0 = kiri, Port IN 1 = kanan."
    min_inputs = 2
    max_inputs = 2
    config_schema = [
        {"name": "keyColumn", "label": "Kolom Kunci (pisah koma untuk multi-key)", "type": "text", "default": "id"},
        {"name": "joinType", "label": "Tipe Join", "type": "select",
         "options": ["inner", "left", "right", "outer"], "default": "inner"},
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if len(inputs) < 2:
            raise NodeExecutionError("Join membutuhkan 2 input (kiri & kanan).")
        keys = split_columns(self.cfg("keyColumn", "id"))
        if not keys:
            raise NodeExecutionError("Kolom kunci join belum diisi.")
        left, right = inputs[0], inputs[1]
        self.require_columns(left, keys)
        self.require_columns(right, keys)
        how = str(self.cfg("joinType", "inner"))
        return pd.merge(left, right, on=keys, how=how, suffixes=("_left", "_right"))
