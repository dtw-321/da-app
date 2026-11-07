from typing import List

import pandas as pd

from app.config.settings import settings
from app.core.sandbox import SandboxError, run_script
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node

DEFAULT_SCRIPT = "df = inputs[0].copy()\ndf['total_ppn'] = df['penjualan'] * 0.11"


@register_node("python_script")
class PythonScriptNode(BaseNode):
    title = "Python Script"
    category = "transforms"
    description = "Transformasi custom: input list 'inputs', output wajib variabel 'df'."
    min_inputs = 1
    config_schema = [
        {"name": "script", "label": "Kode Python (output: df)", "type": "code", "default": DEFAULT_SCRIPT},
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if not settings.ALLOW_PYTHON_SCRIPT:
            raise NodeExecutionError("Node Python Script dinonaktifkan (ALLOW_PYTHON_SCRIPT=false).")
        if not inputs:
            raise NodeExecutionError("Python Script membutuhkan minimal 1 input.")
        try:
            return run_script(str(self.cfg("script", DEFAULT_SCRIPT)), inputs)
        except SandboxError as exc:
            raise NodeExecutionError("Python Script: {}".format(exc))
