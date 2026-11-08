import time
import pandas as pd
from pathlib import Path
from app.engine.nodes.base_node import BaseNode, register_node

@register_node("file_cleanup")
class FileCleanupNode(BaseNode):
    title = "File Cleanup"
    category = "utilities"
    description = "Hapus file lama di folder export secara otomatis."
    max_inputs = 0
    
    config_schema = [
        {"name": "folder_path", "label": "Path Folder", "type": "text", "default": "./export"},
        {"name": "retention_days", "label": "Simpan file selama (hari)", "type": "number", "default": 1},
    ]
    
    def execute(self, inputs: list) -> pd.DataFrame:
        folder = Path(self.config.get("folder_path", "./export"))
        days = float(self.config.get("retention_days", 1))
        
        if not folder.exists() or not folder.is_dir():
            return pd.DataFrame({"file_name": ["-"], "status": ["Folder tidak ditemukan"]})
            
        # Hitung batas waktu (threshold) dalam format timestamp (epoch)
        current_time = time.time()
        threshold = current_time - (days * 86400) # 86400 detik = 1 hari
        
        deleted_files = []
        
        # Iterasi semua file di dalam folder
        for file in folder.iterdir():
            if file.is_file():
                # st_mtime adalah waktu modifikasi terakhir file
                if file.stat().st_mtime < threshold:
                    try:
                        file.unlink() # Hapus file
                        deleted_files.append({"file_name": file.name, "status": "deleted"})
                    except Exception as e:
                        deleted_files.append({"file_name": file.name, "status": f"error: {e}"})
                        
        if not deleted_files:
            deleted_files.append({"file_name": "-", "status": "Tidak ada file yang dihapus"})
            
        return pd.DataFrame(deleted_files)