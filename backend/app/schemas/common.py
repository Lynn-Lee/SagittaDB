"""
公共分页与响应 Schema。
"""
from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PageParams(BaseModel):
    """分页参数（Query 参数用）。"""
    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=200, description="每页数量")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PageResponse(BaseModel, Generic[T]):
    """通用分页响应。"""
    total: int
    page: int
    page_size: int
    items: list[T]


class SuccessResponse(BaseModel):
    """通用成功响应。"""
    status: int = 0
    msg: str = "ok"
    data: Any = None


class ErrorResponse(BaseModel):
    """通用错误响应。"""
    status: int
    msg: str
    detail: str | None = None
