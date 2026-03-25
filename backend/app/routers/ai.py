"""
AI Text2SQL 路由（Pack D）。
调用 Anthropic Claude API 将自然语言转换为 SQL。
系统配置中需配置 ai_api_key 和 ai_model。
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import current_user
from app.models.instance import Instance

logger = logging.getLogger(__name__)
router = APIRouter()


class Text2SQLRequest(BaseModel):
    question: str
    instance_id: int | None = None
    db_name: str | None = None
    dialect_hint: str | None = None  # 可选：手动指定方言


@router.post("/text2sql/", summary="自然语言转 SQL（AI Text2SQL）")
async def text2sql(
    data: Text2SQLRequest,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    将自然语言描述转换为 SQL 语句。
    使用 Claude API（claude-sonnet-4-20250514）。
    需要在系统配置中设置：ai_api_key（Anthropic API Key）。
    """
    if not data.question.strip():
        raise HTTPException(400, "问题描述不能为空")

    # 获取实例信息（用于生成更准确的 SQL）
    db_type = data.dialect_hint or "sql"
    if data.instance_id:
        inst_result = await db.execute(
            select(Instance).where(Instance.id == data.instance_id)
        )
        inst = inst_result.scalar_one_or_none()
        if inst:
            db_type = inst.db_type

    # 读取 AI API Key 配置
    from app.services.system_config import SystemConfigService
    api_key = await SystemConfigService.get_value(db, "ai_api_key")
    ai_model = await SystemConfigService.get_value(db, "ai_model") or "claude-sonnet-4-20250514"

    if not api_key:
        raise HTTPException(400, "AI 功能未配置，请在系统配置中设置 ai_api_key（Anthropic API Key）")

    # 构建 Prompt
    dialect_map = {
        "mysql": "MySQL", "pgsql": "PostgreSQL", "oracle": "Oracle",
        "mssql": "SQL Server", "clickhouse": "ClickHouse", "doris": "Doris",
    }
    dialect_name = dialect_map.get(db_type, "标准SQL")

    system_prompt = f"""你是一个专业的数据库工程师，擅长将自然语言转换为精准的 {dialect_name} SQL 语句。

规则：
1. 只输出 SQL 语句，不要任何解释或 markdown 代码块标记
2. SQL 要符合 {dialect_name} 语法
3. 使用合理的表名和列名（如用户没有提供表结构，根据上下文推断）
4. 对于 DELETE/UPDATE 语句，必须包含 WHERE 条件
5. 适当添加 LIMIT 避免全表扫描
{"6. 当前数据库：" + data.db_name if data.db_name else ""}"""

    user_message = f"请将以下需求转换为 {dialect_name} SQL：\n{data.question}"

    # 调用 Claude API
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": ai_model,
                    "max_tokens": 1024,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_message}],
                },
            )

        if resp.status_code != 200:
            logger.error("claude_api_error: %s %s", resp.status_code, resp.text[:200])
            raise HTTPException(500, f"AI API 调用失败：{resp.status_code}")

        result = resp.json()
        sql = result["content"][0]["text"].strip()

        # 清理可能的 markdown 代码块
        if sql.startswith("```"):
            lines = sql.split("\n")
            sql = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        logger.info("text2sql_success: user=%s db_type=%s", user.get("username"), db_type)
        return {
            "status": 0,
            "sql": sql,
            "db_type": db_type,
            "model": ai_model,
        }

    except httpx.TimeoutException as e:
        raise HTTPException(504, "AI API 请求超时，请重试") from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("text2sql_error: %s", str(e))
        raise HTTPException(500, f"AI 生成失败：{str(e)}") from e
