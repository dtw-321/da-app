"""Konversi DataFrame -> JSON aman (NaN, Timestamp, numpy scalar, dll)."""
import json
from typing import Any, Dict, List, Optional

import pandas as pd


def df_to_records(df: pd.DataFrame, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    if df is None or df.empty:
        return []
    view = df.head(limit) if limit else df
    view = view.copy()
    view.columns = [str(c) for c in view.columns]
    # to_json menangani NaN -> null, datetime -> ISO8601, numpy -> primitive
    return json.loads(view.to_json(orient="records", date_format="iso", double_precision=10))


def df_schema(df: pd.DataFrame) -> List[Dict[str, str]]:
    if df is None:
        return []
    return [{"name": str(col), "dtype": str(dtype)} for col, dtype in df.dtypes.items()]


def build_output(df: pd.DataFrame, limit: int, files: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    total = int(len(df))
    records = df_to_records(df, limit)
    return {
        "totalRows": total,
        "returnedRows": len(records),
        "truncated": total > len(records),
        "columns": df_schema(df),
        "data": records,
        "files": files or [],
    }
