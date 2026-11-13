import pandas as pd
from typing import List
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node

@register_node("clean_missing")
class CleanMissingNode(BaseNode):
    title = "Clean Missing Data"
    category = "transforms"
    description = "Menangani data yang kosong (NaN/Null) dengan menghapus baris atau mengisi nilai default."
    min_inputs = 1
    max_inputs = 1
    config_schema = [
        {
            "name": "action", 
            "label": "Tindakan", 
            "type": "select", 
            "options": ["Drop Rows (Hapus Baris)", "Fill Value (Isi Nilai)"], 
            "default": "Drop Rows (Hapus Baris)"
        },
        {
            "name": "fillValue", 
            "label": "Nilai Pengganti (Jika Fill)", 
            "type": "text", 
            "default": "0"
        }
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if not inputs:
            raise NodeExecutionError("Clean Missing Data membutuhkan input tabel data.")
            
        df = inputs[0]
        action = self.cfg("action", "Drop Rows (Hapus Baris)")
        
        if "Drop" in action:
            # Menghapus semua baris yang memiliki minimal 1 kolom kosong
            return df.dropna()
        else:
            # Mengisi data kosong dengan input pengguna
            fill_val = self.cfg("fillValue", "0")
            # Konversi otomatis ke angka jika memungkinkan agar tipe data tidak rusak
            if fill_val.isnumeric():
                fill_val = float(fill_val) if "." in fill_val else int(fill_val)
            return df.fillna(fill_val)