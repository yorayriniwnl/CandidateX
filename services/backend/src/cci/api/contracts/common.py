"""Common API envelope, pagination, and error response schemas."""

from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    """Structured error detail schema."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    field: Optional[str] = Field(None, description="Request field that caused the error")


class ApiResponse(BaseModel, Generic[DataT]):
    """Standard unified API response wrapper."""
    success: bool = True
    data: Optional[DataT] = None
    errors: List[ErrorDetail] = Field(default_factory=list)


class PaginatedMeta(BaseModel):
    """Pagination metadata."""
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)
    total_pages: int = Field(..., ge=0)


class PaginatedResponse(BaseModel, Generic[DataT]):
    """Paginated collection response envelope."""
    success: bool = True
    data: List[DataT] = Field(default_factory=list)
    pagination: PaginatedMeta
    errors: List[ErrorDetail] = Field(default_factory=list)
