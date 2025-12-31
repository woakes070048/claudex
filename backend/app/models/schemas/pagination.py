from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    model_config = {"populate_by_name": True}

    page: int = Field(default=1, ge=1)
    per_page: int = Field(
        default=10,
        ge=1,
        le=100,
    )


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    page: int
    per_page: int
    total: int
    pages: int


class CursorPaginationParams(BaseModel):
    model_config = {"populate_by_name": True}

    cursor: str | None = Field(default=None)
    limit: int = Field(default=20, ge=1, le=100)


class CursorPaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None
    has_more: bool
