"""Pydantic schemas for the transaction processing system."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CurrencyEnum(str, Enum):
    """Supported currencies."""

    PLN = "PLN"
    EUR = "EUR"
    USD = "USD"


class TransactionCSVRow(BaseModel):
    """Schema for validating CSV row data during import."""

    transaction_id: UUID
    timestamp: datetime
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    currency: CurrencyEnum
    customer_id: UUID
    product_id: UUID
    quantity: int = Field(..., gt=0)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount has max 2 decimal places."""
        if v.as_tuple().exponent < -2:
            raise ValueError("Amount must have at most 2 decimal places")
        return v

    model_config = ConfigDict(str_strip_whitespace=True, use_enum_values=True)


class TransactionCreate(BaseModel):
    """Schema for creating a transaction (internal use after CSV validation)."""

    transaction_id: UUID
    timestamp: datetime
    amount: Decimal
    currency: CurrencyEnum
    customer_id: UUID
    product_id: UUID
    quantity: int


class TransactionResponse(BaseModel):
    """Schema for transaction API responses."""

    transaction_id: UUID
    timestamp: datetime
    amount: Decimal
    currency: CurrencyEnum
    customer_id: UUID
    product_id: UUID
    quantity: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TransactionListParams(BaseModel):
    """Query parameters for transaction list endpoint."""

    customer_id: UUID | None = None
    product_id: UUID | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)

    @property
    def offset(self) -> int:
        """Calculate offset for pagination."""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""

    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


class TransactionListResponse(PaginatedResponse):
    """Paginated response for transaction list."""

    items: list[TransactionResponse]


class CustomerSummaryResponse(BaseModel):
    """Response schema for customer summary report."""

    customer_id: UUID
    total_amount_pln: Decimal = Field(..., description="Total amount spent in PLN")
    unique_products_count: int = Field(..., description="Number of unique products purchased")
    last_transaction_date: datetime | None = Field(None, description="Date of last transaction")

    model_config = ConfigDict(from_attributes=True)


class ProductSummaryResponse(BaseModel):
    """Response schema for product summary report."""

    product_id: UUID
    total_quantity_sold: int = Field(..., description="Total quantity sold")
    total_revenue_pln: Decimal = Field(..., description="Total revenue in PLN")
    unique_customers_count: int = Field(..., description="Number of unique customers")

    model_config = ConfigDict(from_attributes=True)


class FileUploadResponse(BaseModel):
    """Response for CSV file upload."""

    message: str
    processed_count: int
    error_count: int
    errors: list[dict[str, str]] = Field(default_factory=list)


class ValidationError(BaseModel):
    """Schema for validation error details."""

    row_number: int
    field: str | None = None
    error: str
    raw_data: dict[str, str] | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    error_code: str | None = None
    errors: list[ValidationError] | None = None


# Optional: Date range filter for bonus feature
class DateRangeFilter(BaseModel):
    """Date range filter for reports (bonus feature)."""

    start_date: datetime | None = None
    end_date: datetime | None = None

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: datetime | None, info) -> datetime | None:
        """Ensure end_date is after start_date."""
        if v and info.data.get("start_date") and v < info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


# Optional: Auth token schema for bonus feature
class AuthToken(BaseModel):
    """Authentication token schema (bonus feature)."""

    token: str = Field(..., min_length=32)
    token_type: str = "Bearer"


# Currency exchange rates (could be moved to config)
EXCHANGE_RATES: dict[CurrencyEnum, Decimal] = {
    CurrencyEnum.PLN: Decimal("1.0"),
    CurrencyEnum.EUR: Decimal("4.3"),
    CurrencyEnum.USD: Decimal("4.0"),
}
