"""Semua path absolut & penjaga keamanan filesystem (tanpa dependensi app lain)."""
import re
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
EXPORT_DIR = STORAGE_DIR / "exports"
FRONTEND_DIR = BASE_DIR / "frontend"

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def ensure_dirs() -> None:
    for directory in (STORAGE_DIR, UPLOAD_DIR, EXPORT_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def secure_filename(name: str, default: str = "file") -> str:
    """Buang komponen direktori & karakter berbahaya."""
    raw = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode()
    raw = raw.replace("\\", "/").split("/")[-1]
    cleaned = _UNSAFE.sub("_", raw).strip("._")
    return cleaned[:120] or default


def is_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def export_path(filename: str) -> Path:
    """Path tujuan export yang dijamin berada di dalam EXPORT_DIR."""
    target = (EXPORT_DIR / secure_filename(filename)).resolve()
    if not is_within(target, EXPORT_DIR):
        raise ValueError("Nama file export tidak valid.")
    return target


def resolve_source_path(raw_path: str, allow_external: bool = False) -> Path:
    """Validasi path sumber data (anti path traversal / arbitrary file read)."""
    candidate = Path(str(raw_path)).expanduser()
    if not candidate.is_absolute():
        candidate = (UPLOAD_DIR / candidate)
    candidate = candidate.resolve()
    if not candidate.is_file():
        raise FileNotFoundError("File tidak ditemukan: {}".format(candidate))
    if not allow_external and not is_within(candidate, UPLOAD_DIR):
        raise PermissionError(
            "Akses ditolak. File harus berada di storage/uploads "
            "(atau set ALLOW_EXTERNAL_SOURCE_PATH=true)."
        )
    return candidate
