"""DAG executor: validasi -> topological sort -> eksekusi terisolasi per node."""
import heapq
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from app.config.settings import settings
from app.core.serialization import build_output
from app.engine.nodes import NODE_REGISTRY


class WorkflowGraphError(ValueError):
    """Struktur graph tidak valid."""


class WorkflowExecutor:
    def __init__(self, graph: Dict[str, Any], target_node_id: Optional[str] = None,
                 max_preview_rows: Optional[int] = None):
        self.nodes_data: List[Dict[str, Any]] = list(graph.get("nodes") or [])
        self.connections: List[Dict[str, Any]] = list(graph.get("connections") or [])
        self.target_node_id = target_node_id
        self.max_preview_rows = max_preview_rows or settings.MAX_PREVIEW_ROWS
        self.results: Dict[str, pd.DataFrame] = {}
        self.logs: List[Dict[str, Any]] = []
        self.node_status: Dict[str, Dict[str, Any]] = {}
        self.artifacts: List[Dict[str, str]] = []
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._parents: Dict[str, List[str]] = defaultdict(list)
        self._children: Dict[str, List[str]] = defaultdict(list)

    # ------------------------------------------------------------------
    def _log(self, level: str, message: str, node_id: Optional[str] = None) -> None:
        self.logs.append({"level": level, "nodeId": node_id, "message": message})

    def _validate(self) -> None:
        if not self.nodes_data:
            raise WorkflowGraphError("Workflow kosong. Tambahkan minimal satu node.")
        for node in self.nodes_data:
            nid, ntype = node.get("id"), node.get("type")
            if not nid or not ntype:
                raise WorkflowGraphError("Setiap node wajib memiliki 'id' dan 'type'.")
            if nid in self._nodes:
                raise WorkflowGraphError("ID node duplikat: {}".format(nid))
            if ntype not in NODE_REGISTRY:
                raise WorkflowGraphError("Tipe node tidak dikenal: {}".format(ntype))
            self._nodes[nid] = node

        seen: Set[str] = set()
        for conn in self.connections:
            src, dst = conn.get("fromNodeId"), conn.get("toNodeId")
            if src not in self._nodes or dst not in self._nodes:
                raise WorkflowGraphError("Koneksi menggantung: {} -> {}".format(src, dst))
            if src == dst:
                raise WorkflowGraphError("Node tidak boleh terhubung ke dirinya sendiri ({}).".format(src))
            key = "{}->{}:{}".format(src, dst, conn.get("toPort", 0))
            if key in seen:
                continue
            seen.add(key)
            self._children[src].append(dst)
            self._parents[dst].append(src)

        # Urutan input deterministik berdasarkan nomor port IN
        port_of = {
            "{}->{}".format(c.get("fromNodeId"), c.get("toNodeId")): int(c.get("toPort") or 0)
            for c in self.connections
        }
        for dst, parents in self._parents.items():
            parents.sort(key=lambda p: (port_of.get("{}->{}".format(p, dst), 0), p))

        if self.target_node_id and self.target_node_id not in self._nodes:
            raise WorkflowGraphError("Target node tidak ditemukan: {}".format(self.target_node_id))

    def _required_nodes(self) -> Set[str]:
        if not self.target_node_id:
            return set(self._nodes)
        required: Set[str] = set()
        stack = [self.target_node_id]
        while stack:
            current = stack.pop()
            if current in required:
                continue
            required.add(current)
            stack.extend(self._parents.get(current, []))
        return required

    def _topological_order(self, required: Set[str]) -> List[str]:
        in_degree = {nid: 0 for nid in required}
        for nid in required:
            for child in self._children.get(nid, []):
                if child in required:
                    in_degree[child] += 1
        heap = [nid for nid, deg in in_degree.items() if deg == 0]
        heapq.heapify(heap)
        order: List[str] = []
        while heap:
            current = heapq.heappop(heap)
            order.append(current)
            for child in self._children.get(current, []):
                if child not in required:
                    continue
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    heapq.heappush(heap, child)
        if len(order) != len(required):
            cyclic = sorted(required - set(order))
            raise WorkflowGraphError("Workflow mengandung siklus (cycle) pada node: {}".format(cyclic))
        return order

    # ------------------------------------------------------------------
    def execute(self) -> Dict[str, Any]:
        started = time.perf_counter()
        self._validate()
        required = self._required_nodes()
        order = self._topological_order(required)
        self._log("info", "Eksekusi {} node dimulai.".format(len(order)))
        failed = False

        for nid in order:
            info = self._nodes[nid]
            node_cls = NODE_REGISTRY[info["type"]]
            title = info.get("title") or node_cls.title
            parents = self._parents.get(nid, [])

            blocked = [p for p in parents if self.node_status.get(p, {}).get("status") in ("error", "skipped")]
            if blocked:
                failed = True
                self.node_status[nid] = {"status": "skipped", "rows": 0, "durationMs": 0,
                                         "error": "Upstream gagal: {}".format(blocked)}
                self._log("warn", "Node [{}] dilewati karena upstream gagal.".format(title), nid)
                continue

            inputs = [self.results[p] for p in parents]
            tick = time.perf_counter()
            try:
                if len(inputs) < node_cls.min_inputs:
                    raise ValueError("Butuh minimal {} input, diterima {}.".format(node_cls.min_inputs, len(inputs)))
                if node_cls.max_inputs is not None and len(inputs) > node_cls.max_inputs:
                    raise ValueError("Maksimal {} input, diterima {}.".format(node_cls.max_inputs, len(inputs)))
                instance = node_cls(node_id=nid, config=info.get("config") or {})
                output = instance.execute(inputs)
                if not isinstance(output, pd.DataFrame):
                    raise TypeError("Node mengembalikan {}, bukan DataFrame.".format(type(output).__name__))
            except Exception as exc:
                failed = True
                elapsed = int((time.perf_counter() - tick) * 1000)
                self.node_status[nid] = {"status": "error", "rows": 0, "durationMs": elapsed, "error": str(exc)}
                self._log("error", "Node [{}] gagal: {}".format(title, exc), nid)
                continue

            elapsed = int((time.perf_counter() - tick) * 1000)
            self.results[nid] = output
            self.artifacts.extend(instance.artifacts)
            self.node_status[nid] = {"status": "success", "rows": int(len(output)),
                                     "durationMs": elapsed, "error": None}
            self._log("success", "Node [{}] selesai: {} baris ({} ms).".format(title, len(output), elapsed), nid)

        duration = int((time.perf_counter() - started) * 1000)
        self._log("info", "Eksekusi selesai dalam {} ms.".format(duration))
        outputs = {}
        for nid, frame in self.results.items():
            files = [a for a in self.artifacts if a.get("nodeId") in (None, nid)] if False else []
            outputs[nid] = build_output(frame, self.max_preview_rows, files)
        # tempelkan artifact ke node pemiliknya
        for nid in self.results:
            outputs[nid]["files"] = [a for a in self.artifacts if a.get("ownerId") == nid]

        return {
            "status": "error" if failed else "success",
            "durationMs": duration,
            "executionOrder": order,
            "logs": self.logs,
            "nodeStatus": self.node_status,
            "outputs": outputs,
            "artifacts": self.artifacts,
        }
