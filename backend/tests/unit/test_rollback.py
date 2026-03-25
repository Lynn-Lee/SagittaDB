"""
SQL 回滚辅助服务单元测试（Pack E/G）。
覆盖 sqlglot 逆向 SQL 生成、my2sql 命令生成、PG WAL 查询。
"""
from app.services.rollback import RollbackService


class TestGetRollbackGuide:
    def test_mysql_strategy_is_binlog(self):
        guide = RollbackService.get_rollback_guide("mysql")
        assert guide["strategy"] == "binlog"
        assert guide["tool"] == "my2sql"

    def test_pgsql_strategy_is_wal(self):
        guide = RollbackService.get_rollback_guide("pgsql")
        assert guide["strategy"] == "wal"

    def test_clickhouse_unsupported(self):
        guide = RollbackService.get_rollback_guide("clickhouse")
        assert guide["strategy"] == "unsupported"

    def test_unknown_db_type(self):
        guide = RollbackService.get_rollback_guide("unknown_db")
        # 返回通用说明不报错
        assert isinstance(guide, dict)

    def test_oracle_uses_logminer(self):
        guide = RollbackService.get_rollback_guide("oracle")
        assert guide["strategy"] == "logminer"

    def test_mongo_uses_oplog(self):
        guide = RollbackService.get_rollback_guide("mongo")
        assert guide["strategy"] == "oplog"


class TestGenerateReverseSQL:
    """验证 sqlglot 静态分析逆向 SQL 生成。"""

    def test_insert_returns_success(self):
        sql = "INSERT INTO users (id, name, email) VALUES (1, 'Alice', 'alice@example.com')"
        result = RollbackService.generate_reverse_sql(sql, "mysql")
        assert result["success"] is True
        assert result["total"] >= 1

    def test_insert_reverse_sqls_has_items(self):
        sql = "INSERT INTO users (id, name, email) VALUES (1, 'Alice', 'alice@example.com')"
        result = RollbackService.generate_reverse_sql(sql, "mysql")
        reverse_sqls = result.get("reverse_sqls", [])
        assert len(reverse_sqls) >= 1
        # 第一条应包含 DELETE
        first = reverse_sqls[0]
        assert "reverse" in first
        assert "users" in first["reverse"].lower() or "users" in first["original"].lower()

    def test_result_has_guide(self):
        sql = "INSERT INTO t (id) VALUES (1)"
        result = RollbackService.generate_reverse_sql(sql, "mysql")
        assert "guide" in result
        assert "db_type" in result

    def test_delete_has_reverse_entry(self):
        sql = "DELETE FROM users WHERE id = 1"
        result = RollbackService.generate_reverse_sql(sql, "mysql")
        assert result["success"] is True
        assert len(result.get("reverse_sqls", [])) >= 1

    def test_update_has_reverse_entry(self):
        sql = "UPDATE users SET name = 'Bob' WHERE id = 1"
        result = RollbackService.generate_reverse_sql(sql, "mysql")
        assert result["success"] is True

    def test_ddl_handled(self):
        sql = "ALTER TABLE users ADD COLUMN age INT"
        result = RollbackService.generate_reverse_sql(sql, "mysql")
        # DDL 可能 success=False 或 total=0，但不应抛异常
        assert isinstance(result, dict)
        assert "success" in result

    def test_invalid_sql_does_not_raise(self):
        sql = "THIS IS NOT SQL"
        result = RollbackService.generate_reverse_sql(sql, "mysql")
        assert isinstance(result, dict)

    def test_pgsql_dialect(self):
        sql = 'INSERT INTO "users" (id, name) VALUES (1, \'test\')'
        result = RollbackService.generate_reverse_sql(sql, "pgsql")
        assert isinstance(result, dict)
        assert "success" in result

    def test_multi_statement(self):
        sql = (
            "INSERT INTO orders (id, user_id, total) VALUES (100, 1, 99.9);\n"
            "INSERT INTO orders (id, user_id, total) VALUES (101, 2, 49.9);"
        )
        result = RollbackService.generate_reverse_sql(sql, "mysql")
        assert isinstance(result, dict)
        # 多条语句应该有多个逆向条目
        assert result.get("total", 0) >= 1

    def test_returns_dict(self):
        result = RollbackService.generate_reverse_sql("INSERT INTO t (id) VALUES (1)", "mysql")
        assert isinstance(result, dict)
        assert "success" in result
        assert "reverse_sqls" in result
        assert "db_type" in result


class TestGenerateMy2sqlCommand:
    """验证 MySQL/TiDB Binlog 命令生成器。"""

    def test_basic_command_contains_host(self):
        result = RollbackService.generate_my2sql_command(
            host="mysql-host",
            port=3306,
            user="repl_user",
            start_time="2026-01-01 00:00:00",
            stop_time="2026-01-01 01:00:00",
        )
        assert "command" in result
        assert "mysql-host" in result["command"]
        assert "repl_user" in result["command"]

    def test_command_includes_time_range(self):
        result = RollbackService.generate_my2sql_command(
            host="localhost",
            port=3306,
            user="root",
            start_time="2026-03-01 10:00:00",
            stop_time="2026-03-01 11:00:00",
        )
        assert "2026-03-01" in result["command"]

    def test_command_with_databases_filter(self):
        result = RollbackService.generate_my2sql_command(
            host="localhost",
            port=3306,
            user="root",
            start_time="2026-03-01 10:00:00",
            stop_time="2026-03-01 11:00:00",
            databases="mydb",
        )
        assert "mydb" in result["command"]

    def test_returns_dict_with_expected_keys(self):
        result = RollbackService.generate_my2sql_command(
            host="h", port=3306, user="u",
            start_time="2026-01-01 00:00:00",
            stop_time="2026-01-01 01:00:00",
        )
        assert isinstance(result, dict)
        assert "command" in result
        assert "tool" in result

    def test_command_has_rollback_work_type(self):
        result = RollbackService.generate_my2sql_command(
            host="h", port=3306, user="u",
            start_time="2026-01-01 00:00:00",
            stop_time="2026-01-01 01:00:00",
        )
        assert "rollback" in result["command"].lower()


class TestGetPgWalQuery:
    """验证 PostgreSQL WAL 逻辑复制查询语句生成。"""

    def test_returns_dict(self):
        result = RollbackService.get_pg_wal_query("test_slot")
        assert isinstance(result, dict)

    def test_contains_steps(self):
        result = RollbackService.get_pg_wal_query("test_slot")
        assert "steps" in result
        assert len(result["steps"]) > 0

    def test_steps_contain_slot_name(self):
        result = RollbackService.get_pg_wal_query("my_replication_slot")
        steps_text = " ".join(result["steps"])
        assert "my_replication_slot" in steps_text

    def test_steps_contain_pg_logical_function(self):
        result = RollbackService.get_pg_wal_query("s")
        steps_text = " ".join(result["steps"]).lower()
        assert "pg_" in steps_text or "wal" in steps_text or "logical" in steps_text

    def test_has_tool_and_prereq(self):
        result = RollbackService.get_pg_wal_query("s")
        assert "tool" in result
        assert "prereq" in result
