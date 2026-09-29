from typing import Generic, TypeVar, Sequence
from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")

class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    ):
        self.page = page
        self.page_size = page_size
        self.limit = page_size
        self.offset = (page - 1) * page_size

class PaginatedResponse(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    page_size: int
    total_pages: int
