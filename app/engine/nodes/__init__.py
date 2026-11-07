import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Any

# Ekspor NODE_REGISTRY, register_node, dan BaseNode agar dapat diakses dari app.engine.nodes
from app.engine.nodes.base_node import NODE_REGISTRY, register_node, BaseNode

def load_all_nodes():
    """Mengimpor seluruh berkas node di sub-folder sources, transforms, dan exports secara otomatis."""
    package_dir = Path(__file__).parent
    for subfolder in ["sources", "transforms", "exports"]:
        folder_path = package_dir / subfolder
        if folder_path.exists():
            for _, module_name, _ in pkgutil.iter_modules([str(folder_path)]):
                importlib.import_module(f"app.engine.nodes.{subfolder}.{module_name}")

# Otomatis muat semua node saat modul app.engine.nodes di-import
load_all_nodes()