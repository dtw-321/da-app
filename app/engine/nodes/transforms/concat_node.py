import pandas as pd
from typing import List
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node

@register_node("concat")
class ConcatNode(BaseNode):
    title = "Concat (Gabung Baris)"
    category = "transforms"
    description = "Menggabungkan dua tabel data secara vertikal. Port 1 = Tabel Atas, Port 2 = Tabel Bawah."
    min_inputs = 2
    max_inputs = 2
    config_schema = [
        {"name": "topNodeId", "label": "Node Asal Port 1 (Atas)", "type": "text", "default": ""},
        {"name": "bottomNodeId", "label": "Node Asal Port 2 (Bawah)", "type": "text", "default": ""},
        {"name": "ignoreIndex", "label": "Reset Index (Urutkan Ulang)", "type": "select", 
         "options": ["Ya", "Tidak"], "default": "Ya"}
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if len(inputs) < 2:
            raise NodeExecutionError("Concat membutuhkan 2 input tabel data (atas & bawah).")
            
        top_df, bottom_df = inputs[0], inputs[1]
        ignore_idx = self.cfg("ignoreIndex", "Ya") == "Ya"
        
        try:
            # Menggabungkan baris dari kedua tabel
            return pd.concat([top_df, bottom_df], ignore_index=ignore_idx)
        except Exception as e:
            raise NodeExecutionError(f"Gagal melakukan proses concat: {str(e)}")