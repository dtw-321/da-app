import os
import time
import logging
from pathlib import Path

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def cleanup_old_files(folder_path="storage/exports", retention_days=1):
    # Menggunakan Path relatif terhadap root project (data_analityc)
    path = Path(folder_path)
    
    if not path.exists():
        logging.warning(f"Folder {folder_path} tidak ditemukan.")
        return

    # Waktu saat ini dikurangi jumlah hari (dalam detik)
    current_time = time.time()
    threshold = current_time - (retention_days * 86400)
    
    deleted_count = 0
    
    for file in path.iterdir():
        if file.is_file():
            # Cek waktu modifikasi file (st_mtime)
            if file.stat().st_mtime < threshold:
                try:
                    file.unlink()
                    logging.info(f"Berhasil dihapus: {file.name}")
                    deleted_count += 1
                except Exception as e:
                    logging.error(f"Gagal menghapus {file.name}: {e}")
                    
    logging.info(f"Selesai. Total {deleted_count} file dihapus dari {folder_path}.")

if __name__ == "__main__":
    # Jalankan pembersihan untuk folder 'storage/exports' dengan batas waktu 1 hari
    cleanup_old_files(folder_path="storage/exports", retention_days=1)