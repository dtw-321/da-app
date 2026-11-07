"""Kontrak API (pydantic v1 & v2 compatible)."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


class NodePayload(BaseModel):
    id: str
    type: str
    title: Optional[str] = None
    x: Optional[float] = 0
    y: Optional[float] = 0
    config: Dict[str, Any] = Field(default_factory=dict)


class ConnectionPayload(BaseModel):
    fromNodeId: str
    toNodeId: str
    fromPort: Optional[int] = 0
    toPort: Optional[int] = 0


class WorkflowPayload(BaseModel):
    workflowId: Optional[str] = None
    workflowName: Optional[str] = "Untitled Workflow"
    description: Optional[str] = None
    nodes: List[NodePayload] = Field(default_factory=list)
    connections: List[ConnectionPayload] = Field(default_factory=list)
    targetNodeId: Optional[str] = None

    def to_graph(self) -> Dict[str, Any]:
        data = model_to_dict(self)
        return {"nodes": data.get("nodes", []), "connections": data.get("connections", [])}
