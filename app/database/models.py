import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text

from app.database.connection import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class WorkflowModel(Base):
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    graph_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ExecutionLogModel(Base):
    __tablename__ = "execution_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    workflow_id = Column(String(36), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=True, index=True)
    status = Column(String(50), nullable=False)
    logs = Column(JSON, nullable=False)
    duration_ms = Column(String(20), nullable=True)
    executed_at = Column(DateTime, default=datetime.utcnow)
