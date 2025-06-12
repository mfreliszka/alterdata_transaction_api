"""Database models for the transaction processing system."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    DECIMAL,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
# from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import as_declarative, declared_attr

from app.schemas.schemas import CurrencyEnum

@as_declarative()
class Base:
    """Base class for all database models."""

    type_annotation_map = {
        UUID: PostgresUUID(as_uuid=True),
        Decimal: DECIMAL(10, 2),
    }


class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )


class Transaction(Base, TimestampMixin):
    """Transaction model representing a single transaction."""

    __tablename__ = "transactions"

    # Primary key
    transaction_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        index=True,
    )

    # Transaction details
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,  # For date range queries
    )
    amount: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
    )
    currency: Mapped[CurrencyEnum] = mapped_column(
        Enum(CurrencyEnum, name="currency_enum"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Foreign keys
    customer_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("customers.customer_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,  # For filtering
    )
    product_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("products.product_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,  # For filtering
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(
        back_populates="transactions",
        lazy="noload",  # Explicit loading for async
    )
    product: Mapped["Product"] = relationship(
        back_populates="transactions",
        lazy="noload",  # Explicit loading for async
    )

    # Composite indexes for performance
    __table_args__ = (
        Index("idx_customer_timestamp", "customer_id", "timestamp"),
        Index("idx_product_timestamp", "product_id", "timestamp"),
        Index("idx_customer_product", "customer_id", "product_id"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<Transaction(id={self.transaction_id}, "
            f"amount={self.amount} {self.currency}, "
            f"customer={self.customer_id})>"
        )


class Customer(Base, TimestampMixin):
    """Customer model for better data organization."""

    __tablename__ = "customers"

    customer_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        index=True,
    )

    # Optional: Add more customer fields if needed
    # name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="customer",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Customer(id={self.customer_id})>"


class Product(Base, TimestampMixin):
    """Product model for better data organization."""

    __tablename__ = "products"

    product_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        index=True,
    )

    # Optional: Add more product fields if needed
    # name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    # price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2), nullable=True)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="product",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Product(id={self.product_id})>"


# Optional: Import batch tracking for async processing (bonus feature)
class ImportBatch(Base, TimestampMixin):
    """Track CSV import batches for async processing."""

    __tablename__ = "import_batches"

    batch_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        primary_key=True,
        default=func.gen_random_uuid(),
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum("pending", "processing", "completed", "failed", name="import_status_enum"),
        nullable=False,
        default="pending",
    )
    total_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    processed_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error_rows: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    error_details: Mapped[str | None] = mapped_column(
        String,  # JSON string for error details
        nullable=True,
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<ImportBatch(id={self.batch_id}, status={self.status})>"
