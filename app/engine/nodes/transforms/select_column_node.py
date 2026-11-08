import pandas as pd
from typing import List
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node, split_columns

@register_node("select_column")
class SelectColumnNode(BaseNode):
    title = "Select Columns"
    category = "transforms"
    description = "Memilih dan mempertahankan hanya kolom-kolom tertentu dari tabel data."
    min_inputs = 1
    max_inputs = 1
    config_schema = [
        {
            "name": "columns", 
            "label": "Nama Kolom (pisahkan dengan koma)", 
            "type": "text", 
            "default": ""
        }
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if not inputs:
            raise NodeExecutionError("Select Columns membutuhkan input tabel data dari node sebelumnya.")
            
        df = inputs[0]
        
        # Mengambil daftar kolom dari konfigurasi
        cols_raw = self.cfg("columns", "")
        if not cols_raw.strip():
            raise NodeExecutionError("Konfigurasi kolom kosong. Masukkan setidaknya satu nama kolom yang ingin dipilih.")
            
        # Gunakan fungsi bawaan split_columns dari base_node
        selected_cols = split_columns(cols_raw)
        
        # Validasi apakah kolom-kolom yang diminta benar-benar ada di dalam DataFrame
        self.require_columns(df, selected_cols)
        
        # Mengembalikan DataFrame yang hanya berisi kolom terpilih
        return df[selected_cols]