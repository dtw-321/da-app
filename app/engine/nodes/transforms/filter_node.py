from typing import List

import pandas as pd

from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node

OPERATORS = ["==", "!=", ">", ">=", "<", "<=", "contains", "not_contains", "is_null", "not_null"]


@register_node("filter_rows")
class FilterRowsNode(BaseNode):
    title = "Row Filter"
    category = "transforms"
    description = "Menyaring baris berdasarkan kondisi sederhana."
    min_inputs = 1
    max_inputs = 1
    config_schema = [
        {"name": "column", "label": "Kolom", "type": "text", "default": "penjualan"},
        {"name": "operator", "label": "Operator", "type": "select", "options": OPERATORS, "default": ">"},
        {"name": "value", "label": "Nilai Pembanding", "type": "text", "default": "1000000"},
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        df = inputs[0]
        column = str(self.cfg("column", "")).strip()
        operator = str(self.cfg("operator", "==")).strip()
        raw = self.config.get("value", "")
        self.require_columns(df, [column])
        series = df[column]

        if operator == "is_null":
            return df[series.isna()].copy()
        if operator == "not_null":
            return df[series.notna()].copy()
        if operator in ("contains", "not_contains"):
            mask = series.astype(str).str.contains(str(raw), case=False, na=False, regex=False)
            return df[mask if operator == "contains" else ~mask].copy()

        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().any():
            try:
                left, right = numeric, float(raw)
            except (TypeError, ValueError):
                raise NodeExecutionError("Nilai pembanding harus numerik untuk kolom ini.")
        else:
            left, right = series.astype(str), str(raw)

        ops = {
            "==": lambda a, b: a == b, "!=": lambda a, b: a != b,
            ">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
            "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
        }
        if operator not in ops:
            raise NodeExecutionError("Operator tidak didukung: {}".format(operator))
        return df[ops[operator](left, right).fillna(False)].copy()
