import pandas as pd
from typing import List
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node, split_columns

@register_node("aggregate")
class AggregateNode(BaseNode):
    title = "Aggregate"
    category = "transforms"
    description = """Mengelompokkan data dan melakukan perhitungan/penggabungan berbeda pada tiap kolom. 
        fungsi agregasi yang didukung: sum, mean, count, max, min, first, last, median, std, var"""
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
            "name": "targetColumns", 
            "label": "Kolom Target (pisah koma, misal: harga, nama_barang)", 
            "type": "text", 
            "default": ""
        },
        {
            "name": "aggFunctions", 
            "label": "Tipe Agregasi (urut sesuai kolom, misal: sum, concat)", 
            "type": "text", 
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
        target_cols_raw = self.cfg("targetColumns", "")
        agg_funcs_raw = self.cfg("aggFunctions", "")
        separator = self.cfg("separator", ", ")
        
        group_cols = split_columns(group_cols_raw)
        target_cols = split_columns(target_cols_raw)
        agg_funcs = [f.strip().lower() for f in agg_funcs_raw.split(",") if f.strip()]
        
        if not group_cols or not target_cols or not agg_funcs:
            raise NodeExecutionError("Kolom 'Group By', 'Kolom Target', dan 'Tipe Agregasi' wajib diisi.")
            
        # Validasi jumlah kolom target harus sama dengan jumlah tipe agregasi
        if len(target_cols) != len(agg_funcs):
            raise NodeExecutionError(
                f"Jumlah Kolom Target ({len(target_cols)}) tidak sama dengan jumlah Tipe Agregasi ({len(agg_funcs)})."
            )
            
        # Validasi ketersediaan seluruh kolom di dalam DataFrame
        self.require_columns(df, group_cols + target_cols)
        
        # Daftar fungsi bawaan Pandas yang diizinkan
        valid_pandas_funcs = ["sum", "mean", "count", "max", "min", "first", "last", "median", "std", "var"]
        agg_dict = {}
        
        # Memetakan setiap kolom ke fungsi agregasinya masing-masing
        for col, func_name in zip(target_cols, agg_funcs):
            if func_name == "concat":
                # Menggunakan fungsi custom untuk menggabungkan string dan mengabaikan NaN
                agg_dict[col] = lambda x, sep=separator: sep.join(x.dropna().astype(str))
            elif func_name in valid_pandas_funcs:
                agg_dict[col] = func_name
            else:
                raise NodeExecutionError(
                    f"Fungsi agregasi '{func_name}' tidak didukung. Gunakan: {', '.join(valid_pandas_funcs + ['concat'])}."
                )
                
        try:
            # Mengeksekusi proses agregasi multi-kolom
            result_df = df.groupby(group_cols, as_index=False).agg(agg_dict)
            return result_df
            
        except Exception as e:
            raise NodeExecutionError(f"Gagal melakukan proses agregasi: {str(e)}")