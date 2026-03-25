"""ClickHouse 引擎（Pack E）- clickhouse-connect HTTP 协议。"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.core.security import decrypt_field
from app.engines.models import ResultSet, ReviewSet, SqlItem

if TYPE_CHECKING:
    from app.models.instance import Instance

logger = logging.getLogger(__name__)


class ClickHouseEngine:
    name = "ClickHouseEngine"
    db_type = "clickhouse"

    def __init__(self, instance: Instance) -> None:
        self.instance = instance

    def _client(self, db_name: str | None = None):
        try:
            import clickhouse_connect
        except ImportError:
            raise ImportError("pip install clickhouse-connect") from None
        return clickhouse_connect.get_client(
            host=self.instance.host,
            port=self.instance.port or 8123,
            username=decrypt_field(self.instance.user),
            password=decrypt_field(self.instance.password),
            database=db_name or self.instance.db_name or "default",
            connect_timeout=10,
            send_receive_timeout=300,
        )

    async def test_connection(self) -> ResultSet:
        rs = ResultSet()
        try:
            v = self._client().command("SELECT version()")
            rs.column_list = ["version"]
            rs.rows = [(str(v),)]
        except Exception as e:
            rs.error = str(e)
        return rs

    def escape_string(self, value: str) -> str:
        return value.replace("'", "\\'")

    async def get_all_databases(self) -> ResultSet:
        rs = ResultSet()
        try:
            r = self._client().query("SHOW DATABASES")
            rs.column_list = ["database"]
            rs.rows = [(row[0],) for row in r.result_rows
                       if row[0] not in ("system", "information_schema", "INFORMATION_SCHEMA")]
        except Exception as e:
            rs.error = str(e)
        return rs

    async def get_all_tables(self, db_name: str, **kw: Any) -> ResultSet:
        rs = ResultSet()
        try:
            r = self._client(db_name).query(
                "SELECT name FROM system.tables WHERE database={db:String} ORDER BY name",
                parameters={"db": db_name})
            rs.column_list = ["table_name"]
            rs.rows = [(row[0],) for row in r.result_rows]
        except Exception as e:
            rs.error = str(e)
        return rs

    async def get_all_columns_by_tb(self, db_name: str, tb_name: str, **kw: Any) -> ResultSet:
        rs = ResultSet()
        try:
            r = self._client(db_name).query(
                "SELECT name,type,default_expression,comment FROM system.columns "
                "WHERE database={db:String} AND table={tb:String} ORDER BY position",
                parameters={"db": db_name, "tb": tb_name})
            rs.column_list = ["column_name", "column_type", "column_default", "column_comment"]
            rs.rows = list(r.result_rows)
        except Exception as e:
            rs.error = str(e)
        return rs

    async def describe_table(self, db_name: str, tb_name: str, **kw: Any) -> ResultSet:
        rs = ResultSet()
        try:
            r = self._client(db_name).query(f"DESCRIBE TABLE `{db_name}`.`{tb_name}`")
            rs.column_list = list(r.column_names)
            rs.rows = list(r.result_rows)
        except Exception as e:
            rs.error = str(e)
        return rs

    async def get_tables_metas_data(self, db_name: str, **kw: Any) -> list:
        try:
            r = self._client(db_name).query(
                "SELECT name,engine,total_rows,total_bytes,comment FROM system.tables WHERE database={db:String}",
                parameters={"db": db_name})
            return [{"table_name": r[0], "engine": r[1], "rows": r[2], "bytes": r[3], "comment": r[4]}
                    for r in r.result_rows]
        except Exception:
            return []

    def query_check(self, db_name: str, sql: str) -> dict:
        for kw in ["insert", "update", "delete", "drop", "truncate", "alter"]:
            if sql.strip().lower().startswith(kw):
                return {"msg": f"在线查询不允许 {kw.upper()}", "syntax_error": True}
        return {"msg": "", "syntax_error": False}

    def filter_sql(self, sql: str, limit_num: int) -> str:
        sql = sql.rstrip(";").strip()
        if limit_num > 0 and "limit" not in sql.lower():
            sql = f"{sql} LIMIT {limit_num}"
        return sql

    async def query(self, db_name: str, sql: str, limit_num: int = 0, parameters: dict | None = None, **kw: Any) -> ResultSet:
        rs = ResultSet()
        try:
            r = self._client(db_name).query(self.filter_sql(sql, limit_num), parameters=parameters)
            rs.column_list = list(r.column_names)
            rs.rows = list(r.result_rows)
            rs.affected_rows = len(rs.rows)
        except Exception as e:
            rs.error = str(e)
        return rs

    def query_masking(self, db_name: str, sql: str, resultset: ResultSet) -> ResultSet:
        return resultset

    async def execute_check(self, db_name: str, sql: str) -> ReviewSet:
        import sqlglot
        review = ReviewSet(full_sql=sql)
        try:
            for i, stmt in enumerate(sqlglot.parse(sql, dialect="clickhouse")):
                item = SqlItem(id=i+1, sql=str(stmt))
                if isinstance(stmt, (sqlglot.exp.Update, sqlglot.exp.Delete)):
                    item.errlevel = 1
                    item.errormessage = "ClickHouse 请使用 ALTER TABLE...UPDATE/DELETE"
                review.rows.append(item)
        except Exception as e:
            review.rows.append(SqlItem(id=1, sql=sql, errlevel=2, errormessage=str(e)))
        return review

    async def execute(self, db_name: str, sql: str, **kw: Any) -> ReviewSet:
        review = ReviewSet(full_sql=sql)
        try:
            client = self._client(db_name)
            for i, stmt in enumerate(s.strip() for s in sql.split(";") if s.strip()):
                try:
                    client.command(stmt)
                    review.rows.append(SqlItem(id=i+1, sql=stmt, stagestatus="Executed Successfully"))
                except Exception as e:
                    review.rows.append(SqlItem(id=i+1, sql=stmt, errlevel=2, errormessage=str(e)))
                    review.error = str(e)
                    break
        except Exception as e:
            review.error = str(e)
        return review

    async def execute_workflow(self, workflow: Any) -> ReviewSet:
        sql = workflow.content.sql_content if workflow.content else ""
        return await self.execute(workflow.db_name, sql)

    async def processlist(self, **kw: Any) -> ResultSet:
        rs = ResultSet()
        try:
            r = self._client().query(
                "SELECT query_id,user,elapsed,query FROM system.processes ORDER BY elapsed DESC")
            rs.column_list = ["query_id", "user", "elapsed_sec", "query"]
            rs.rows = list(r.result_rows)
        except Exception as e:
            rs.error = str(e)
        return rs

    async def collect_metrics(self) -> dict:
        try:
            client = self._client()
            m = {row[0]: row[1] for row in client.query(
                "SELECT metric,value FROM system.metrics LIMIT 50").result_rows}
            return {"health": {"up": 1}, "metrics": m}
        except Exception as e:
            return {"health": {"up": 0}, "error": str(e)}

    def get_supported_metric_groups(self) -> list:
        return ["health", "metrics"]
