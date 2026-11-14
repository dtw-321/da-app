"""REST controller tipis: validasi I/O, delegasi ke engine."""
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.paths import EXPORT_DIR, UPLOAD_DIR, ensure_dirs, export_path, secure_filename
from app.database.connection import get_db
from app.database.models import ExecutionLogModel, WorkflowModel
from app.engine.executor import WorkflowExecutor, WorkflowGraphError
from app.engine.nodes import NODE_REGISTRY
from app.engine.python_generator import PythonScriptGenerator
from app.schemas.workflow import WorkflowPayload, model_to_dict

router = APIRouter(prefix="/api/workflow", tags=["Workflow Engine"])
ALLOWED_EXT = {".csv", ".txt", ".tsv", ".xlsx", ".xls", ".json"}


# @router.get("/specs")
# def get_node_specs() -> List[Dict[str, Any]]:
#     return [cls.spec() for _, cls in sorted(NODE_REGISTRY.items())]

@router.get("/specs")
def get_node_specs() -> List[Dict[str, Any]]:
    """Otomatis menghasilkan spesifikasi UI untuk setiap Node berdasarkan config_schema di Python."""
    specs = []
    for node_type, cls in NODE_REGISTRY.items():
        specs.append({
            "type": node_type,
            "title": getattr(cls, "title", node_type.replace("_", " ").title()),
            "category": getattr(cls, "category", "transforms"),
            "description": getattr(cls, "description", ""),
            "config_schema": getattr(cls, "config_schema", [])
        })
    return specs


@router.post("/run")
def run_workflow(payload: WorkflowPayload, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        executor = WorkflowExecutor(payload.to_graph(), target_node_id=payload.targetNodeId)
        result = executor.execute()
    except WorkflowGraphError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Kesalahan engine: {}".format(exc))

    # tandai pemilik artifact agar frontend bisa menampilkan tombol unduh per node
    try:
        db.add(ExecutionLogModel(workflow_id=payload.workflowId, status=result["status"].upper(),
                                 logs=result["logs"], duration_ms=str(result["durationMs"])))
        db.commit()
    except Exception:
        db.rollback()
    return result


@router.post("/generate-python")
def generate_python(payload: WorkflowPayload) -> Dict[str, str]:
    try:
        return {"code": PythonScriptGenerator(payload.to_graph()).generate()}
    except WorkflowGraphError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, str]:
    ensure_dirs()
    original = secure_filename(file.filename or "upload.dat")
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_EXT:
        raise HTTPException(status_code=415, detail="Ekstensi {} tidak didukung.".format(suffix))

    target = UPLOAD_DIR / "{}_{}".format(uuid.uuid4().hex[:8], original)
    limit = settings.MAX_UPLOAD_MB * 1024 * 1024
    written = 0
    try:
        with open(target, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > limit:
                    raise HTTPException(status_code=413, detail="Ukuran file melebihi {} MB.".format(settings.MAX_UPLOAD_MB))
                buffer.write(chunk)
    except HTTPException:
        target.unlink(missing_ok=True) if hasattr(target, "unlink") else None
        raise
    finally:
        await file.close()
    return {"status": "success", "filePath": str(target), "fileName": original}


@router.get("/download/{filename}")
def download_export_file(filename: str) -> FileResponse:
    try:
        path = export_path(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File ekspor tidak ditemukan.")
    return FileResponse(path=path, filename=path.name, media_type="application/octet-stream")


@router.post("/save")
def save_workflow(payload: dict, db: Session = Depends(get_db)):
    # Ambil payload yang dikirim dari fungsi payload() di app.js
    workflow_name = payload.get("workflowName", "Untitled Workflow").strip()
    
    graph_data = {
        "nodes": payload.get("nodes", []),
        "connections": payload.get("connections", [])
    }
    
    # 1. Cek apakah workflow dengan nama tersebut sudah ada di DB
    existing_workflow = db.query(WorkflowModel).filter(WorkflowModel.name == workflow_name).first()
    
    if existing_workflow:
        # 2A. UPDATE JIKA UNIQUE (Nama sudah terdaftar)
        existing_workflow.graph_data = graph_data
        db.commit()
        db.refresh(existing_workflow)
        
        return {
            "status": "success", 
            "message": f"Workflow '{workflow_name}' berhasil diperbarui.", 
            "id": existing_workflow.id
        }
    else:
        # 2B. INSERT (Nama belum terdaftar)
        new_id = str(uuid.uuid4())
        new_workflow = WorkflowModel(
            id=new_id,
            name=workflow_name,
            graph_data=graph_data
        )
        db.add(new_workflow)
        db.commit()
        db.refresh(new_workflow)
        
        return {
            "status": "success", 
            "message": f"Workflow '{workflow_name}' baru berhasil disimpan.", 
            "id": new_workflow.id
        }

@router.get("/list")
def list_workflows(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    rows = db.query(WorkflowModel).order_by(WorkflowModel.updated_at.desc()).limit(200).all()
    return [{"id": w.id, "name": w.name, "nodes": len((w.graph_data or {}).get("nodes", [])),
             "updated_at": w.updated_at.strftime("%Y-%m-%d %H:%M") if w.updated_at else "-"} for w in rows]


@router.get("/load/{wf_id}")
def load_workflow(wf_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    wf = db.query(WorkflowModel).filter(WorkflowModel.id == wf_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow tidak ditemukan.")
    return {"id": wf.id, "name": wf.name, "graph_data": wf.graph_data}


@router.delete("/{wf_id}")
def delete_workflow(wf_id: str, db: Session = Depends(get_db)) -> Dict[str, str]:
    wf = db.query(WorkflowModel).filter(WorkflowModel.id == wf_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow tidak ditemukan.")
    db.delete(wf)
    db.commit()
    return {"status": "success"}
