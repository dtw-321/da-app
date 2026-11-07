import pytest

from app.core.sandbox import SandboxError, run_script
from app.engine.executor import WorkflowExecutor, WorkflowGraphError


def _node(nid, ntype, config=None):
    return {"id": nid, "type": ntype, "title": ntype, "config": config or {}}


def test_sample_csv_to_aggregate():
    graph = {
        "nodes": [_node("a", "csv_reader", {"sampleData": True}),
                  _node("b", "aggregate", {"groupBy": "kategori", "targetColumn": "penjualan", "aggFunction": "SUM"})],
        "connections": [{"fromNodeId": "a", "toNodeId": "b", "toPort": 0}],
    }
    result = WorkflowExecutor(graph).execute()
    assert result["status"] == "success"
    assert result["outputs"]["b"]["totalRows"] == 2


def test_cycle_detected():
    graph = {
        "nodes": [_node("a", "csv_reader"), _node("b", "aggregate")],
        "connections": [{"fromNodeId": "a", "toNodeId": "b"}, {"fromNodeId": "b", "toNodeId": "a"}],
    }
    with pytest.raises(WorkflowGraphError):
        WorkflowExecutor(graph).execute()


def test_target_pruning():
    graph = {
        "nodes": [_node("a", "csv_reader"), _node("b", "aggregate"), _node("c", "manual_variable")],
        "connections": [{"fromNodeId": "a", "toNodeId": "b"}],
    }
    result = WorkflowExecutor(graph, target_node_id="b").execute()
    assert set(result["executionOrder"]) == {"a", "b"}


def test_error_propagation_marks_skipped():
    graph = {
        "nodes": [_node("a", "csv_reader", {"sampleData": True}),
                  _node("b", "aggregate", {"groupBy": "tidak_ada", "targetColumn": "penjualan"})],
        "connections": [{"fromNodeId": "a", "toNodeId": "b"}],
    }
    result = WorkflowExecutor(graph).execute()
    assert result["status"] == "error"
    assert result["nodeStatus"]["b"]["status"] == "error"


def test_sandbox_blocks_dangerous_code():
    import pandas as pd
    frame = pd.DataFrame({"penjualan": [1000]})
    with pytest.raises(SandboxError):
        run_script("import os\ndf = inputs[0]", [frame])
    with pytest.raises(SandboxError):
        run_script("df = ().__class__.__bases__", [frame])
    out = run_script("df = inputs[0].copy()\ndf['x'] = df['penjualan'] * 2", [frame])
    assert out["x"].iloc[0] == 2000
