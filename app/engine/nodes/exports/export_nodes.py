import os
import pandas as pd
from openpyxl import load_workbook
from typing import List
from app.engine.nodes.base_node import BaseNode, NodeExecutionError, register_node

EXPORT_DIR = os.path.join(os.getcwd(), "storage", "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

@register_node("export_csv")
class ExportCsvNode(BaseNode):
    title = "Export CSV"
    category = "exports"
    min_inputs = 1
    max_inputs = 1
    config_schema = [
        {"name": "filename", "label": "Nama File", "type": "text", "default": "output.csv"}
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if not inputs:
            raise NodeExecutionError("Export membutuhkan input tabel data.")
            
        df = inputs[0]
        filename = self.cfg("filename", "output.csv")
        if not filename.endswith(".csv"):
            filename += ".csv"
            
        file_path = os.path.join(EXPORT_DIR, filename)
        
        try:
            df.to_csv(file_path, index=False)
        except Exception as e:
            raise NodeExecutionError(f"Gagal menyimpan CSV: {str(e)}")
            
        return df  # <--- WAJIB MENGEMBALIKAN DATAFRAME


@register_node("export_excel")
class ExportExcelNode(BaseNode):
    title = "Export Excel"
    category = "exports"
    description = "Mengekspor data ke format Excel dengan dukungan format kolom (date, currency, custom format)."
    min_inputs = 1
    max_inputs = 1
    config_schema = [
        {"name": "filename", "label": "Nama File", "type": "text", "default": "output.xlsx"},
        {"name": "sheetName", "label": "Nama Sheet", "type": "text", "default": "Sheet1"},
        {
            "name": "formatConfig",
            "label": "Format Kolom (Format: kolom:format, pisah dengan titik koma). Contoh: tanggal_lahir:yyyy-mm-dd; penghasilan:Rp #,##0; diskon:0.00%",
            "type": "text",
            "default": ""
        }
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        if not inputs:
            raise NodeExecutionError("Export membutuhkan input tabel data.")
            
        df = inputs[0]
        filename = self.cfg("filename", "output.xlsx")
        if not filename.endswith((".xlsx", ".xls")):
            filename += ".xlsx"
            
        sheet_name = self.cfg("sheetName", "Sheet1")
        file_path = os.path.join(EXPORT_DIR, filename)
        
        try:
            # 1. Simpan DataFrame ke Excel terlebih dahulu menggunakan pandas
            df.to_excel(file_path, index=False, sheet_name=sheet_name)
            
            # 2. Ambil konfigurasi format kolom dari UI Inspector
            format_raw = self.cfg("formatConfig", "").strip()
            if format_raw:
                # Muat workbook menggunakan openpyxl untuk mengatur format sel
                wb = load_workbook(file_path)
                ws = wb[sheet_name]
                
                # Parsing string konfigurasi (contoh: "tanggal:YYYY-MM-DD, penghasilan:Rp #,##0")
                format_dict = {}
                for item in format_raw.split(";"):
                    if ":" in item:
                        col_name, fmt_str = item.split(":", 1)
                        format_dict[col_name.strip().lower()] = fmt_str.strip()
                
                # Petakan nama kolom header (baris 1) ke nomor indeks kolom Excel
                header_map = {}
                for col_idx, cell in enumerate(ws[1], start=1):
                    if cell.value:
                        header_map[str(cell.value).strip().lower()] = col_idx
                        
                # Terapkan format number/date ke setiap baris data pada kolom terkait
                for col_name, fmt_str in format_dict.items():
                    if col_name in header_map:
                        c_idx = header_map[col_name]
                        for row in range(2, ws.max_row + 1):
                            cell = ws.cell(row=row, column=c_idx)
                            if cell.value is not None:
                                cell.number_format = fmt_str
                                
                wb.save(file_path)
                
        except Exception as e:
            raise NodeExecutionError(f"Gagal menyimpan atau memformat Excel: {str(e)}")
            
        return df