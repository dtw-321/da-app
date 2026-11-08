import os
import pandas as pd
from typing import List
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node

EXPORT_DIR = os.path.join(os.getcwd(), "storage", "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

@register_node("export_csv")
class ExportCsvNode(BaseNode):
    title = "Export CSV"
    category = "exports"
    min_inputs = 1
    max_inputs = 1
    config_schema = [
        {"name": "filename", "label": "Nama File", "type": "text", "default": "output.csv"}
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if not inputs:
            raise NodeExecutionError("Export membutuhkan input tabel data.")
            
        df = inputs[0]
        filename = self.cfg("filename", "output.csv")
        if not filename.endswith(".csv"):
            filename += ".csv"
            
        file_path = os.path.join(EXPORT_DIR, filename)
        
        try:
            df.to_csv(file_path, index=False)
        except Exception as e:
            raise NodeExecutionError(f"Gagal menyimpan CSV: {str(e)}")
            
        return df  # <--- WAJIB MENGEMBALIKAN DATAFRAME


@register_node("export_excel")
class ExportExcelNode(BaseNode):
    title = "Export Excel"
    category = "exports"
    min_inputs = 1
    max_inputs = 1
    config_schema = [
        {"name": "filename", "label": "Nama File", "type": "text", "default": "output.xlsx"},
        {"name": "sheetName", "label": "Nama Sheet", "type": "text", "default": "Sheet1"}
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if not inputs:
            raise NodeExecutionError("Export membutuhkan input tabel data.")
            
        df = inputs[0]
        filename = self.cfg("filename", "output.xlsx")
        if not filename.endswith((".xlsx", ".xls")):
            filename += ".xlsx"
            
        file_path = os.path.join(EXPORT_DIR, filename)
        
        try:
            df.to_excel(file_path, index=False, sheet_name=self.cfg("sheetName", "Sheet1"))
        except Exception as e:
            raise NodeExecutionError(f"Gagal menyimpan Excel: {str(e)}")
            
        return df  # <--- WAJIB MENGEMBALIKAN DATAFRAME