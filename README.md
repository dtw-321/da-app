# DTAnalitycs Web Studio Engine

Aplikasi **data analytics visual** dengan arsitektur
**DAG executor** di backend dan **canvas drag-and-drop** di frontend.

- **Backend**: Python 3.8+, FastAPI, SQLAlchemy, pandas
- **Frontend**: Vue 3 via CDN (tanpa Node.js / tanpa build step)
- **Storage**: SQLite (default) atau PostgreSQL

---

## 1. Fitur

| Fitur | Keterangan |
|---|---|
| Visual DAG editor | Drag node dari katalog, sambungkan port OUT → IN, zoom, autosave localStorage |
| Dynamic node registry | Cukup tambah file di `app/engine/nodes/**`, otomatis muncul di katalog |
| Partial execution | Klik ▶ pada node → hanya cabang upstream yang dieksekusi |
| Inspector dinamis | Form dibangun otomatis dari `config_schema` tiap node |
| Preview aman | Maksimal `MAX_PREVIEW_ROWS` baris, NaN/Timestamp di-serialize dengan benar |
| Status per node | success / error / skipped + durasi eksekusi + log berwarna |
| Export & download | Node export menghasilkan artifact yang bisa diunduh dari canvas |
| Python generator | Workflow → script pandas mandiri (`.py`) yang reproducible |
| Persistensi | Simpan/buka workflow ke database, export/import JSON |

## 2. Quickstart

```bash
# 1. buat virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. install dependency
pip install -r requirements.txt

# 3. konfigurasi
cp .env.example .env             # Windows: copy .env.example .env

# 4. inisialisasi database (opsional, otomatis saat startup)
python scripts/init_db.py

# 5. jalankan
python run.py --reload
