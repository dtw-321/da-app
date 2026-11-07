"""Mengubah graph workflow menjadi script pandas mandiri (reproducible)."""
import re
from typing import Any, Dict, List

from app.engine.executor import WorkflowExecutor
from app.engine.nodes import NODE_REGISTRY
from app.engine.nodes.sources.manual_variable_node import parse_variables


def _var(node_id: str) -> str:
    return "df_" + re.sub(r"[^0-9a-zA-Z_]", "_", node_id)


def _q(value: Any) -> str:
    return repr("" if value is None else str(value))


class PythonScriptGenerator:
    def __init__(self, graph: Dict[str, Any]):
        self._executor = WorkflowExecutor(graph)

    def generate(self) -> str:
        ex = self._executor
        ex._validate()
        order = ex._topological_order(ex._required_nodes())
        lines: List[str] = [
            '"""Script hasil generate DTAnalitycs Web Studio Engine."""',
            "import os",
            "import pandas as pd",
            "",
        ]
        for nid in order:
            node = ex._nodes[nid]
            parents = ex._parents.get(nid, [])
            lines.append("")
            lines.append("# --- {} ({}) ---".format(node.get("title") or node["type"], nid))
            lines.extend(self._emit(node, parents, _var(nid)))
        lines += ["", 'if __name__ == "__main__":']
        tail = _var(order[-1]) if order else None
        lines.append("    print({}.head())".format(tail) if tail else "    pass")
        return "\n".join(lines) + "\n"

    def _emit(self, node: Dict[str, Any], parents: List[str], out: str) -> List[str]:
        ntype = node["type"]
        cfg = node.get("config") or {}
        src = [_var(p) for p in parents]
        first = src[0] if src else "pd.DataFrame()"

        if ntype in ("csv_reader", "text_reader"):
            return ["{} = pd.read_csv({}, sep={})".format(out, _q(cfg.get("filePath", "data.csv")),
                                                          _q(cfg.get("delimiter", ",")))]
        if ntype == "excel_reader":
            return ["{} = pd.read_excel({}, sheet_name={})".format(out, _q(cfg.get("filePath", "data.xlsx")),
                                                                   _q(cfg.get("sheetName", "0")))]
        if ntype == "json_reader":
            return ["{} = pd.read_json({})".format(out, _q(cfg.get("filePath", "data.json")))]
        if ntype == "manual_variable":
            return ["{} = pd.DataFrame({!r})".format(out, parse_variables(cfg.get("variables")))]
        if ntype == "db_connector":
            return [
                "from sqlalchemy import create_engine, text",
                '# Set kredensial via environment variable, jangan hardcode.',
                '_engine = create_engine(os.environ.get("SOURCE_DB_URL", "sqlite:///local.db"))',
                "{} = pd.read_sql(text({}), _engine)".format(out, _q(cfg.get("query", "SELECT 1"))),
            ]
        if ntype == "join_node":
            if len(src) < 2:
                return ["# Join dilewati: butuh 2 input", "{} = {}".format(out, first)]
            return ["{} = pd.merge({}, {}, on={}, how={})".format(
                out, src[0], src[1], _q(cfg.get("keyColumn", "id")), _q(cfg.get("joinType", "inner")))]
        if ntype == "aggregate":
            func = {"SUM": "sum", "AVG": "mean", "COUNT": "count", "MIN": "min",
                    "MAX": "max", "MEDIAN": "median"}.get(str(cfg.get("aggFunction", "SUM")).upper(), "sum")
            groups = [g.strip() for g in str(cfg.get("groupBy", "")).split(",") if g.strip()]
            target = str(cfg.get("targetColumn", ""))
            return ["{} = {}.groupby({!r})[{!r}].agg({!r}).reset_index()".format(out, first, groups, target, func)]
        if ntype == "filter_rows":
            col, op, val = _q(cfg.get("column")), str(cfg.get("operator", "==")), _q(cfg.get("value"))
            if op in ("contains", "not_contains"):
                neg = "" if op == "contains" else "~"
                return ["{o} = {i}[{n}{i}[{c}].astype(str).str.contains({v}, case=False, na=False)].copy()".format(
                    o=out, i=first, n=neg, c=col, v=val)]
            if op in ("is_null", "not_null"):
                method = "isna" if op == "is_null" else "notna"
                return ["{} = {}[{}[{}].{}()].copy()".format(out, first, first, col, method)]
            return ["{o} = {i}[pd.to_numeric({i}[{c}], errors='coerce') {op} float({v})].copy()".format(
                o=out, i=first, c=col, op=op, v=val)]
        if ntype == "python_script":
            body = str(cfg.get("script", "df = inputs[0].copy()"))
            code = ["inputs = [{}]".format(", ".join(src)), "scope = {'inputs': inputs, 'pd': pd}",
                    "exec({!r}, scope)".format(body)]
            return code + ["{} = scope['df']".format(out)]
        if ntype == "export_csv":
            return ["{o} = {i}.copy()".format(o=out, i=first),
                    "{}.to_csv({!r}, index=False)".format(out, "storage/exports/{}.csv".format(cfg.get("fileName", "export_data")))]
        if ntype == "export_excel":
            return ["{o} = {i}.copy()".format(o=out, i=first),
                    "{}.to_excel({!r}, index=False)".format(out, "storage/exports/{}.xlsx".format(cfg.get("fileName", "export_data")))]
        cls = NODE_REGISTRY.get(ntype)
        return ["# TODO: node '{}' belum punya emitter ({}).".format(ntype, getattr(cls, "title", ntype)),
                "{} = {}".format(out, first)]
