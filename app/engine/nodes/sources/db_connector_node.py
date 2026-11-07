import re
from functools import lru_cache
from typing import Any, Dict, List
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text

from app.engine.nodes.base_node import BaseNode, NodeExecutionError, as_bool, register_node

_PARAM_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
_READ_ONLY_RE = re.compile(r"^\s*(select|with|show|describe|explain)\b", re.IGNORECASE)


@lru_cache(maxsize=8)
def _cached_engine(conn_str: str):
    return create_engine(conn_str, pool_pre_ping=True, future=True)


def build_connection_string(cfg: Dict[str, Any]) -> str:
    db_type = str(cfg.get("dbEngine", "postgresql"))
    if db_type == "sqlite":
        return "sqlite:///{}".format(cfg.get("dbName", "local.db"))
    user = quote_plus(str(cfg.get("user", "")))
    password = quote_plus(str(cfg.get("password", "")))
    host = cfg.get("host", "localhost")
    port = cfg.get("port", "5432")
    name = cfg.get("dbName", "")
    driver = "mysql+pymysql" if db_type == "mysql" else "postgresql"
    return "{}://{}:{}@{}:{}/{}".format(driver, user, password, host, port, name)


def bind_variables(query: str, variables: Dict[str, Any]):
    """Ubah {var} -> :var lalu bind secara aman (anti SQL injection)."""
    keys = set(_PARAM_RE.findall(query))
    if not keys:
        return text(query), {}
    missing = [k for k in keys if k not in variables]
    if missing:
        raise NodeExecutionError("Variabel query belum tersedia: {}".format(sorted(missing)))
    params = {k: variables[k] for k in keys}
    return text(_PARAM_RE.sub(lambda m: ":" + m.group(1), query)), params


@register_node("db_connector")
class DbConnectorNode(BaseNode):
    title = "DB Connector"
    category = "sources"
    description = "Query database dengan parameter ter-bind dari node upstream."
    max_inputs = 1
    config_schema = [
        {"name": "dbEngine", "label": "Database Engine", "type": "select",
         "options": ["postgresql", "mysql", "sqlite"], "default": "postgresql"},
        {"name": "host", "label": "Host", "type": "text", "default": "localhost"},
        {"name": "port", "label": "Port", "type": "text", "default": "5432"},
        {"name": "user", "label": "Username", "type": "text", "default": "postgres"},
        {"name": "password", "label": "Password", "type": "password", "default": ""},
        {"name": "dbName", "label": "Nama Database", "type": "text", "default": "mydatabase"},
        {"name": "query", "label": "SQL (gunakan {nama_var} untuk parameter)", "type": "textarea",
         "default": "SELECT * FROM orders WHERE status = {status_order}"},
        {"name": "allowWrite", "label": "Izinkan query non-SELECT (berbahaya)", "type": "checkbox", "default": False},
    ]

    def execute(self, inputs: List[pd.DataFrame]) -> pd.DataFrame:
        query = str(self.cfg("query", "SELECT 1")).strip().rstrip(";")
        if not query:
            raise NodeExecutionError("Query SQL kosong.")
        if not as_bool(self.config.get("allowWrite"), False) and not _READ_ONLY_RE.match(query):
            raise NodeExecutionError("Hanya query read-only (SELECT/WITH) yang diizinkan.")

        variables: Dict[str, Any] = {}
        if inputs and not inputs[0].empty:
            frame = inputs[0]
            if {"key", "value"}.issubset(frame.columns):
                variables = {str(r["key"]): r["value"] for _, r in frame.iterrows()}
            else:
                variables = frame.iloc[0].to_dict()

        statement, params = bind_variables(query, variables)
        engine = _cached_engine(build_connection_string(self.config))
        try:
            with engine.connect() as conn:
                return pd.read_sql(statement, con=conn, params=params)
        except Exception as exc:
            raise NodeExecutionError("Query gagal: {}".format(exc))
