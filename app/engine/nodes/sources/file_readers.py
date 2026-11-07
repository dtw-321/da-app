"""Node pembaca file (CSV, Excel, JSON, TXT) dengan base class DRY."""
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from app.config.settings import settings
from app.core.paths import resolve_source_path
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, as_bool, register_node

_FILE_FIELD = {"name": "filePath", "label": "Path File (hasil upload)", "type": "text", "default": ""}
_UPLOAD_FIELD = {"name": "fileUpload", "label": "Upload File", "type": "file", "target": "filePath"}
_SAMPLE_FIELD = {"name": "sampleData", "label": "Pakai data contoh bila path kosong", "type": "checkbox", "default": True}


class _BaseFileReader(BaseNode):
    category = "sources"
    max_inputs = 0
    config_schema: List[Dict[str, Any]] = [_UPLOAD_FIELD, _FILE_FIELD, _SAMPLE_FIELD]

    def _read(self, path: Path) -> pd.DataFrame:
        raise NotImplementedError

    def _sample(self) -> pd.DataFrame:
        return pd.DataFrame()

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        raw = str(self.config.get("filePath") or "").strip()
        if not raw:
            if as_bool(self.config.get("sampleData"), True):
                return self._sample()
            raise NodeExecutionError("Path file belum diisi. Upload file atau isi filePath.")
        path = resolve_source_path(raw, settings.ALLOW_EXTERNAL_SOURCE_PATH)
        try:
            return self._read(path)
        except NodeExecutionError:
            raise
        except Exception as exc:
            raise NodeExecutionError("Gagal membaca {}: {}".format(path.name, exc))


@register_node("csv_reader")
class CsvReaderNode(_BaseFileReader):
    title = "CSV Reader"
    description = "Membaca file CSV menjadi tabel."
    config_schema = _BaseFileReader.config_schema + [
        {"name": "delimiter", "label": "Delimiter", "type": "text", "default": ","},
        {"name": "encoding", "label": "Encoding", "type": "text", "default": "utf-8"},
    ]

    def _read(self, path: Path) -> pd.DataFrame:
        delimiter = str(self.cfg("delimiter", ",")).replace("\\t", "\t")
        return pd.read_csv(path, sep=delimiter, encoding=str(self.cfg("encoding", "utf-8")))

    def _sample(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"id": 1, "nama": "Budi", "kategori": "Elektronik", "penjualan": 1500000},
            {"id": 2, "nama": "Siti", "kategori": "Pakaian", "penjualan": 350000},
            {"id": 3, "nama": "Rudi", "kategori": "Elektronik", "penjualan": 4200000},
        ])


@register_node("excel_reader")
class ExcelReaderNode(_BaseFileReader):
    title = "Excel Reader"
    description = "Membaca file .xlsx berdasarkan nama/index sheet."
    config_schema = _BaseFileReader.config_schema + [
        {"name": "sheetName", "label": "Nama Sheet / Index", "type": "text", "default": "0"},
    ]

    def _read(self, path: Path) -> pd.DataFrame:
        sheet: Any = str(self.cfg("sheetName", "0"))
        try:
            sheet = int(sheet)
        except ValueError:
            pass
        return pd.read_excel(path, sheet_name=sheet)

    def _sample(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"id": 1, "produk": "Laptop", "harga": 12000000, "stok": 15},
            {"id": 2, "produk": "Mouse", "harga": 250000, "stok": 50},
        ])


@register_node("json_reader")
class JsonReaderNode(_BaseFileReader):
    title = "JSON Reader"
    description = "Membaca file JSON (array of object / records)."

    def _read(self, path: Path) -> pd.DataFrame:
        return pd.read_json(path)

    def _sample(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"id": 1, "user": "admin", "role": "Superadmin"},
            {"id": 2, "user": "analyst", "role": "Data Analyst"},
        ])


@register_node("text_reader")
class TextReaderNode(_BaseFileReader):
    title = "Text Reader"
    description = "Membaca file teks ter-delimiter (TSV/log)."
    config_schema = _BaseFileReader.config_schema + [
        {"name": "delimiter", "label": "Delimiter", "type": "text", "default": "\\t"},
    ]

    def _read(self, path: Path) -> pd.DataFrame:
        delimiter = str(self.cfg("delimiter", "\t")).replace("\\t", "\t")
        return pd.read_csv(path, sep=delimiter)

    def _sample(self) -> pd.DataFrame:
        return pd.DataFrame([
            {"log_id": "LOG_001", "level": "INFO", "message": "Booted successfully"},
            {"log_id": "LOG_002", "level": "WARN", "message": "High RAM usage"},
        ])
