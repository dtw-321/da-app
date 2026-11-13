import pandas as pd
from typing import List
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node, split_columns

@register_node("remove_duplicate")
class RemoveDuplicateNode(BaseNode):
    title = "Remove Duplicates"
    category = "transforms"
    description = "Menghapus baris data yang memiliki nilai ganda/duplikat."
    min_inputs = 1
    max_inputs = 1
    config_schema = [
        {"name": "subsetColumns", "label": "Kolom Acuan (Koma untuk multi, kosong = semua kolom)", "type": "text", "default": ""},
        {"name": "keepOption", "label": "Baris yang Dipertahankan", "type": "select", 
         "options": ["first", "last", "none"], "default": "first"}
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if not inputs:
            raise NodeExecutionError("Remove Duplicates membutuhkan input tabel data.")
            
        df = inputs[0]
        cols_raw = self.cfg("subsetColumns", "").strip()
        keep_val = self.cfg("keepOption", "first")
        
        # Jika opsi 'none' dipilih, Pandas menggunakan parameter False
        if keep_val == "none":
            keep_val = False
            
        # Jika kolom acuan diisi, pisahkan menjadi list dan validasi eksistensinya
        subset = split_columns(cols_raw) if cols_raw else None
        if subset:
            self.require_columns(df, subset)
            
        try:
            return df.drop_duplicates(subset=subset, keep=keep_val)
        except Exception as e:
            raise NodeExecutionError(f"Gagal menghapus duplikat: {str(e)}")