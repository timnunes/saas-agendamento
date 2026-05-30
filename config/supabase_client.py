"""
Cliente de banco de dados usando psycopg2 direto.
Contorna o problema de DNS do httpx no Streamlit Cloud.
Usa Session Pooler IPv4 do Supabase.
"""
import os
import streamlit as st
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()


def get_db_conn():
    """Retorna conexão psycopg2 cacheada."""
    if "db_conn" not in st.session_state or st.session_state.db_conn.closed:
        try:
            db_url = st.secrets["DATABASE_URL"].strip()
        except Exception:
            db_url = os.environ.get("DATABASE_URL", "").strip()

        if not db_url:
            st.error("❌ DATABASE_URL não configurada.")
            st.stop()

        conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
        conn.autocommit = True
        st.session_state.db_conn = conn

    return st.session_state.db_conn


class SupabaseTable:
    """Simula a interface do SDK Supabase usando psycopg2."""

    def __init__(self, conn, table_name):
        self.conn = conn
        self.table = table_name
        self._select = "*"
        self._filters = []
        self._order = None
        self._limit = None
        self._data = None
        self._operation = "select"

    def select(self, cols="*"):
        self._select = cols
        return self

    def insert(self, data):
        self._operation = "insert"
        self._data = data
        return self

    def update(self, data):
        self._operation = "update"
        self._data = data
        return self

    def delete(self):
        self._operation = "delete"
        return self

    def eq(self, col, val):
        self._filters.append((col, "=", val))
        return self

    def neq(self, col, val):
        self._filters.append((col, "!=", val))
        return self

    def gte(self, col, val):
        self._filters.append((col, ">=", val))
        return self

    def lte(self, col, val):
        self._filters.append((col, "<=", val))
        return self

    def gt(self, col, val):
        self._filters.append((col, ">", val))
        return self

    def lt(self, col, val):
        self._filters.append((col, "<", val))
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def ilike(self, col, pattern):
        self._filters.append((col, "ILIKE", pattern))
        return self

    def in_(self, col, values):
        self._filters.append((col, "IN", values))
        return self

    def or_(self, condition):
        self._filters.append(("__or__", condition, None))
        return self

    def execute(self):
        cur = self.conn.cursor()
        try:
            if self._operation == "select":
                sql = f'SELECT {self._select} FROM "{self.table}"'
                params = []
                where = self._build_where(params)
                if where:
                    sql += f" WHERE {where}"
                if self._order:
                    direction = "DESC" if self._order[1] else "ASC"
                    sql += f' ORDER BY "{self._order[0]}" {direction}'
                if self._limit:
                    sql += f" LIMIT {self._limit}"
                cur.execute(sql, params)
                rows = cur.fetchall()
                return type("Result", (), {"data": [dict(r) for r in rows]})()

            elif self._operation == "insert":
                if isinstance(self._data, list):
                    rows = self._data
                else:
                    rows = [self._data]
                for row in rows:
                    cols = ", ".join([f'"{k}"' for k in row.keys()])
                    placeholders = ", ".join(["%s"] * len(row))
                    sql = f'INSERT INTO "{self.table}" ({cols}) VALUES ({placeholders})'
                    cur.execute(sql, list(row.values()))
                return type("Result", (), {"data": []})()

            elif self._operation == "update":
                sets = ", ".join([f'"{k}" = %s' for k in self._data.keys()])
                params = list(self._data.values())
                sql = f'UPDATE "{self.table}" SET {sets}'
                where_params = []
                where = self._build_where(where_params)
                if where:
                    sql += f" WHERE {where}"
                    params += where_params
                cur.execute(sql, params)
                return type("Result", (), {"data": []})()

            elif self._operation == "delete":
                sql = f'DELETE FROM "{self.table}"'
                params = []
                where = self._build_where(params)
                if where:
                    sql += f" WHERE {where}"
                cur.execute(sql, params)
                return type("Result", (), {"data": []})()

        except Exception as e:
            self.conn.rollback()
            raise e
        finally:
            cur.close()

    def _build_where(self, params):
        parts = []
        for f in self._filters:
            col, op, val = f
            if col == "__or__":
                parts.append(f"({op})")
            elif op == "IN":
                placeholders = ", ".join(["%s"] * len(val))
                parts.append(f'"{col}" IN ({placeholders})')
                params.extend(val)
            else:
                parts.append(f'"{col}" {op} %s')
                params.append(val)
        return " AND ".join(parts)


class SupabaseClient:
    """Cliente simplificado compatível com a interface do SDK Supabase."""

    def __init__(self, conn):
        self.conn = conn

    def table(self, name):
        return SupabaseTable(self.conn, name)


def get_supabase():
    """Retorna cliente compatível com SDK Supabase usando psycopg2."""
    if "supabase_client" not in st.session_state:
        conn = get_db_conn()
        st.session_state.supabase_client = SupabaseClient(conn)
    return st.session_state.supabase_client
