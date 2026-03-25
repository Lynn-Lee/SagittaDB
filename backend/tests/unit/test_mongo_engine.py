"""
MongoDB 引擎单元测试。
验证 shell=True 命令注入漏洞（P0-1）修复：
所有查询通过 pymongo Driver，不调用任何 subprocess。
"""
import contextlib

import pytest

from app.engines.mongo import MongoEngine


class MockInstance:
    host = "localhost"
    port = 27017
    user = ""       # 空表示不加密
    password = ""
    db_name = ""
    show_db_name_regex = ""


class TestMongoQueryParser:
    """测试 MongoDB 查询语句安全解析（不经过 shell）。"""

    def setup_method(self):
        self.engine = MongoEngine(instance=MockInstance())

    def test_parse_find_simple(self):
        parsed = self.engine._parse_mongo_query(
            'db.users.find({"status": "active"})'
        )
        assert parsed["type"] == "find"
        assert parsed["collection"] == "users"
        assert parsed["filter"] == {"status": "active"}

    def test_parse_find_empty_filter(self):
        parsed = self.engine._parse_mongo_query("db.users.find({})")
        assert parsed["type"] == "find"
        assert parsed["filter"] == {}

    def test_parse_find_with_projection(self):
        parsed = self.engine._parse_mongo_query(
            'db.users.find({"age": {"$gt": 18}}, {"name": 1, "email": 1})'
        )
        assert parsed["type"] == "find"
        assert parsed["projection"] == {"name": 1, "email": 1}

    def test_parse_aggregate(self):
        parsed = self.engine._parse_mongo_query(
            'db.orders.aggregate([{"$match": {"status": "paid"}}, {"$group": {"_id": "$user_id"}}])'
        )
        assert parsed["type"] == "aggregate"
        assert parsed["collection"] == "orders"
        assert len(parsed["pipeline"]) == 2

    def test_parse_count(self):
        parsed = self.engine._parse_mongo_query(
            'db.users.count({"active": true})'
        )
        assert parsed["type"] == "count"
        assert parsed["collection"] == "users"

    def test_injection_attempt_semicolon(self):
        """验证分号注入无效（不通过 shell 执行）。"""
        # 攻击向量：; rm -rf /（shell 注入）
        # 修复后：_parse_mongo_query 只解析 MongoDB 语法，
        # 不传给 shell，分号无法造成命令注入
        with pytest.raises(ValueError, match="不支持的 MongoDB 查询格式"):
            self.engine._parse_mongo_query(
                "db.users.find({}); rm -rf /"
            )

    def test_injection_attempt_pipe(self):
        """验证管道符注入无效。"""
        with pytest.raises(ValueError, match="不支持的 MongoDB 查询格式"):
            self.engine._parse_mongo_query(
                "db.users.find({}) | cat /etc/passwd"
            )

    def test_injection_attempt_backtick(self):
        """验证反引号命令替换无效。"""
        with pytest.raises(ValueError, match="不支持的 MongoDB 查询格式"):
            self.engine._parse_mongo_query(
                "db.users.find(`whoami`)"
            )

    def test_unsupported_operation_raises(self):
        """不支持的操作类型应该抛出 ValueError，而不是尝试执行。"""
        with pytest.raises(ValueError):
            self.engine._parse_mongo_query("db.users.drop()")

    def test_no_subprocess_called(self):
        """验证 MongoEngine 不调用任何 subprocess（核心安全保证）。"""
        import unittest.mock as mock

        with mock.patch("subprocess.Popen") as mock_popen:
            with contextlib.suppress(Exception):
                self.engine._parse_mongo_query('db.users.find({"id": 1})')
            # subprocess.Popen 不应该被调用
            mock_popen.assert_not_called()

    def test_query_check_valid(self):
        result = self.engine.query_check("testdb", 'db.users.find({"age": 18})')
        assert result["syntax_error"] is False
        assert result["msg"] == ""

    def test_query_check_invalid(self):
        result = self.engine.query_check("testdb", "INVALID QUERY")
        assert result["syntax_error"] is True
        assert result["msg"] != ""
