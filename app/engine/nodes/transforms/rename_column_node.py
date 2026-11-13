import pandas as pd
from typing import List
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node

@register_node("rename_column")
class RenameColumnNode(BaseNode):
    title = "Rename Column"
    category = "transforms"
    description = "Mengubah nama satu kolom menjadi nama baru."
    min_inputs = 1
    max_inputs = 1
    config_schema = [
        {"name": "oldName", "label": "Nama Kolom Lama", "type": "text", "default": ""},
        {"name": "newName", "label": "Nama Kolom Baru", "type": "text", "default": ""}
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if not inputs:
            raise NodeExecutionError("Rename Column membutuhkan input tabel data.")
            
        df = inputs[0]
        old_col = self.cfg("oldName", "").strip()
        new_col = self.cfg("newName", "").strip()
        
        if not old_col or not new_col:
            raise NodeExecutionError("Nama kolom lama dan baru harus diisi.")
            
        if old_col not in df.columns:
            raise NodeExecutionError(f"Kolom '{old_col}' tidak ditemukan di dalam tabel data.")
            
        return df.rename(columns={old_col: new_col})