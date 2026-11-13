import pandas as pd
from typing import List
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node, split_columns

@register_node("aggregate")
class AggregateNode(BaseNode):
    title = "Aggregate"
    category = "transforms"
    description = "Mengelompokkan data berdasarkan kolom tertentu dan melakukan perhitungan atau penggabungan teks."
    min_inputs = 1
    max_inputs = 1
    config_schema = [
        {
            "name": "groupColumns", 
            "label": "Kolom Group By (pisah koma)", 
            "type": "text", 
            "default": ""
        },
        {
            "name": "targetColumn", 
            "label": "Kolom Target Agregasi", 
            "type": "text", 
            "default": ""
        },
        {
            "name": "aggFunction", 
            "label": "Fungsi Agregasi", 
            "type": "select", 
            "options": ["sum", "mean", "count", "max", "min", "concat"], 
            "default": "sum"
        },
        {
            "name": "separator", 
            "label": "Karakter Pemisah (Khusus Concat)", 
            "type": "text", 
            "default": ", "
        }
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if not inputs:
            raise NodeExecutionError("Aggregate membutuhkan input tabel data dari node sebelumnya.")
            
        df = inputs[0]
        
        # Membaca konfigurasi dari UI
        group_cols_raw = self.cfg("groupColumns", "")
        target_col = self.cfg("targetColumn", "").strip()
        agg_type = self.cfg("aggFunction", "sum")
        separator = self.cfg("separator", ", ")
        
        group_cols = split_columns(group_cols_raw)
        
        if not group_cols or not target_col:
            raise NodeExecutionError("Kolom 'Group By' dan 'Kolom Target' wajib diisi.")
            
        # Validasi ketersediaan kolom di dalam tabel
        self.require_columns(df, group_cols + [target_col])
        
        try:
            # Penentuan fungsi agregasi
            if agg_type == "concat":
                # Mengubah data menjadi string, membuang baris kosong (NaN), dan menggabungkannya
                agg_func = lambda x: separator.join(x.dropna().astype(str))
            else:
                # Menggunakan fungsi bawaan pandas (sum, mean, dll)
                agg_func = agg_type
                
            # Mengeksekusi proses agregasi
            result_df = df.groupby(group_cols, as_index=False).agg({target_col: agg_func})
            
            return result_df
            
        except Exception as e:
            raise NodeExecutionError(f"Gagal melakukan proses agregasi: {str(e)}")