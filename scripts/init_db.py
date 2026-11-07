"""Inisialisasi tabel database secara manual: python scripts/init_db.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.connection import Base, engine  # noqa: E402
from app.database.models import ExecutionLogModel, WorkflowModel  # noqa: E402,F401


def init_db() -> None:
    print("Membuat tabel pada:", engine.url)
    Base.metadata.create_all(bind=engine)
    print("Selesai.")


if __name__ == "__main__":
    init_db()
