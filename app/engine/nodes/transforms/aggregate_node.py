from typing import List

import pandas as pd

from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node, split_columns

FUNC_MAP = {"SUM": "sum", "AVG": "mean", "COUNT": "count", "MIN": "min", "MAX": "max", "MEDIAN": "median"}


@register_node("aggregate")
class AggregateNode(BaseNode):
    title = "Aggregate"
    category = "transforms"
    description = "Group by + agregasi numerik."
    min_inputs = 1
    max_inputs = 1
    config_schema = [
        {"name": "groupBy", "label": "Group By (pisah koma)", "type": "text", "default": "kategori"},
        {"name": "targetColumn", "label": "Kolom Target", "type": "text", "default": "penjualan"},
        {"name": "aggFunction", "label": "Fungsi", "type": "select",
         "options": list(FUNC_MAP.keys()), "default": "SUM"},
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        df = inputs[0].copy()
        groups = split_columns(self.cfg("groupBy"))
        target = str(self.cfg("targetColumn", "")).strip()
        label = str(self.cfg("aggFunction", "SUM")).upper()
        func = FUNC_MAP.get(label)
        if func is None:
            raise NodeExecutionError("Fungsi agregasi tidak dikenal: {}".format(label))
        if not target:
            raise NodeExecutionError("Kolom target agregasi belum diisi.")
        self.require_columns(df, groups + [target])
        if df.empty:
            return pd.DataFrame(columns=groups + ["{}_{}".format(label, target)])
        if func != "count":
            df[target] = pd.to_numeric(df[target], errors="coerce")
        result = df.groupby(groups, dropna=False)[target].agg(func).reset_index()
        return result.rename(columns={target: "{}_{}".format(label, target)})
