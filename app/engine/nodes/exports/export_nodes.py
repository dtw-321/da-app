from typing import List

import pandas as pd

from app.core.paths import EXPORT_DIR, ensure_dirs, export_path
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node


class _BaseExport(BaseNode):
    category = "exports"
    min_inputs = 1
    max_inputs = 1
    extension = "csv"
    config_schema = [
        {"name": "fileName", "label": "Nama File Hasil (tanpa ekstensi)", "type": "text", "default": "export_data"},
    ]

    def _write(self, df: pd.DataFrame, path) -> None:
        raise NotImplementedError

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        df = inputs[0].copy()
        ensure_dirs()
        name = "{}.{}".format(self.cfg("fileName", "export_data"), self.extension)
        path = export_path(name)
        try:
            self._write(df, path)
        except Exception as exc:
            raise NodeExecutionError("Gagal menulis file {}: {}".format(path.name, exc))
        self.artifacts.append({"fileName": path.name, "url": "/api/workflow/download/{}".format(path.name)})
        return df


@register_node("export_csv")
class ExportCsvNode(_BaseExport):
    title = "Export CSV"
    description = "Menyimpan hasil ke storage/exports/*.csv"
    extension = "csv"
    config_schema = _BaseExport.config_schema + [
        {"name": "delimiter", "label": "Delimiter", "type": "text", "default": ","},
    ]

    def _write(self, df: pd.DataFrame, path) -> None:
        df.to_csv(path, index=False, sep=str(self.cfg("delimiter", ",")))


@register_node("export_excel")
class ExportExcelNode(_BaseExport):
    title = "Export Excel"
    description = "Menyimpan hasil ke storage/exports/*.xlsx"
    extension = "xlsx"

    def _write(self, df: pd.DataFrame, path) -> None:
        df.to_excel(path, index=False)
