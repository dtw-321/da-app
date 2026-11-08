import pandas as pd
from typing import List
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node

@register_node("string_manipulation")
class StringManipulationNode(BaseNode):
    title = "String Manipulation"
    category = "transforms"
    description = "Memanipulasi teks pada kolom (Uppercase, Trim, Replace, dll)."
    min_inputs = 1
    max_inputs = 1
    config_schema = [
        {"name": "inputColumn", "label": "Kolom Input", "type": "text", "default": ""},
        {"name": "operation", "label": "Operasi", "type": "select", 
         "options": ["UPPERCASE", "LOWERCASE", "TITLECASE", "TRIM", "REPLACE"], "default": "UPPERCASE"},
        {"name": "replaceOld", "label": "Teks Lama (Khusus Replace)", "type": "text", "default": ""},
        {"name": "replaceNew", "label": "Teks Baru (Khusus Replace)", "type": "text", "default": ""},
        {"name": "outputColumn", "label": "Nama Kolom Output (Kosongkan jika ingin menimpa)", "type": "text", "default": ""}
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if not inputs:
            raise NodeExecutionError("Butuh input data tabel.")
            
        df = inputs[0].copy()
        in_col = self.cfg("inputColumn", "")
        out_col = self.cfg("outputColumn", "")
        if not out_col.strip():
            out_col = in_col  # Timpa kolom jika output kosong
            
        self.require_columns(df, [in_col])
        
        # Pastikan data di-cast ke string sebelum dimanipulasi
        series = df[in_col].astype(str)
        operation = self.cfg("operation", "UPPERCASE")
        
        if operation == "UPPERCASE":
            df[out_col] = series.str.upper()
        elif operation == "LOWERCASE":
            df[out_col] = series.str.lower()
        elif operation == "TITLECASE":
            df[out_col] = series.str.title()
        elif operation == "TRIM":
            df[out_col] = series.str.strip()
        elif operation == "REPLACE":
            old_txt = self.cfg("replaceOld", "")
            new_txt = self.cfg("replaceNew", "")
            df[out_col] = series.str.replace(old_txt, new_txt, regex=False)
            
        return df