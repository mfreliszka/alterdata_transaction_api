"""Service layer implementing business logic."""

from csv import DictReader
import io
import json
import logging
import secrets
from datetime import datetime
from decimal import Decimal
from typing import BinaryIO
from uuid import UUID

from app.core.config import settings
from app.repositories.repositories import (
    CustomerRepository,
    ImportBatchRepository,
    ProductRepository,
    TransactionRepository,
)
from app.schemas.schemas import (
    EXCHANGE_RATES,
    CurrencyEnum,
    CustomerSummaryResponse,
    FileUploadResponse,
    ProductSummaryResponse,
    TransactionCreate,
    TransactionCSVRow,
    TransactionListParams,
    TransactionListResponse,
    TransactionResponse,
    ValidationError,
)

logger = logging.getLogger(__name__)


class TransactionService:
    """Service for transaction business logic."""

    def __init__(
        self,
        transaction_repo: TransactionRepository,
        customer_repo: CustomerRepository,
        product_repo: ProductRepository,
    ) -> None:
        """Initialize service with repositories."""
        self.transaction_repo = transaction_repo
        self.customer_repo = customer_repo
        self.product_repo = product_repo

    async def get_transaction(self, transaction_id: UUID) -> TransactionResponse | None:
        """Get transaction by ID."""
        transaction = await self.transaction_repo.get_by_id(transaction_id)
        if not transaction:
            return None

        return TransactionResponse.model_validate(transaction)

    async def list_transactions(
        self,
        params: TransactionListParams,
    ) -> TransactionListResponse:
        """List transactions with pagination and filtering."""
        transactions, total = await self.transaction_repo.get_paginated(
            customer_id=params.customer_id,
            product_id=params.product_id,
            offset=params.offset,
            limit=params.page_size,
        )

        # Calculate pagination metadata
        total_pages = (total + params.page_size - 1) // params.page_size

        return TransactionListResponse(
            items=[TransactionResponse.model_validate(t) for t in transactions],
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        )

    async def create_transaction(
        self,
        transaction_data: TransactionCreate,
    ) -> TransactionResponse:
        """Create a single transaction."""
        # Ensure customer and product exist
        await self.customer_repo.get_or_create(transaction_data.customer_id)
        await self.product_repo.get_or_create(transaction_data.product_id)

        # Create transaction
        transaction = await self.transaction_repo.create(transaction_data)

        return TransactionResponse.model_validate(transaction)


class ImportService:
    """Service for CSV import operations."""

    def __init__(
        self,
        transaction_repo: TransactionRepository,
        customer_repo: CustomerRepository,
        product_repo: ProductRepository,
        import_batch_repo: ImportBatchRepository | None = None,
    ) -> None:
        """Initialize service with repositories."""
        self.transaction_repo = transaction_repo
        self.customer_repo = customer_repo
        self.product_repo = product_repo
        self.import_batch_repo = import_batch_repo

    async def import_csv(
        self,
        file: BinaryIO,
        filename: str,
    ) -> FileUploadResponse:
        """Import transactions from CSV file."""
        # Track import batch if repository available
        batch = None
        if self.import_batch_repo:
            batch = await self.import_batch_repo.create(filename=filename)

        try:
            # Parse and validate CSV
            valid_transactions, errors, total_rows = await self._parse_csv(file)

            # Update batch with total rows
            if batch and self.import_batch_repo:
                await self.import_batch_repo.update_status(
                    batch.batch_id,
                    status="processing",
                    processed_rows=0,
                    error_rows=len(errors),
                )

            # Process valid transactions
            if valid_transactions:
                await self._process_transactions(valid_transactions)

            # Update batch status
            if batch and self.import_batch_repo:
                await self.import_batch_repo.update_status(
                    batch.batch_id,
                    status="completed",
                    processed_rows=len(valid_transactions),
                    error_rows=len(errors),
                    error_details=json.dumps([e.model_dump() for e in errors]) if errors else None,
                )

            # Log summary
            logger.info(
                f"CSV import completed: {len(valid_transactions)} processed, "
                f"{len(errors)} errors from {total_rows} total rows",
            )

            return FileUploadResponse(
                message=f"Successfully processed {len(valid_transactions)} transactions",
                processed_count=len(valid_transactions),
                error_count=len(errors),
                errors=[
                    {
                        "row": str(e.row_number),
                        "error": e.error,
                        "field": e.field or "general",
                    }
                    for e in errors
                ],
            )

        except Exception as e:
            # Update batch status on failure
            if batch and self.import_batch_repo:
                await self.import_batch_repo.update_status(
                    batch.batch_id,
                    status="failed",
                    error_details=str(e),
                )

            logger.error(f"CSV import failed: {e!s}")
            raise

    async def _parse_csv(
        self,
        file: BinaryIO,
    ) -> tuple[list[TransactionCreate], list[ValidationError], int]:
        """Parse and validate CSV file."""
        valid_transactions: list[TransactionCreate] = []
        errors: list[ValidationError] = []

        # Read file content
        content = file.read()
        text_content = content.decode("utf-8-sig")  # Handle BOM

        # Parse CSV
        csv_reader = DictReader(io.StringIO(text_content))

        # Validate headers
        required_headers = {
            "transaction_id",
            "timestamp",
            "amount",
            "currency",
            "customer_id",
            "product_id",
            "quantity",
        }

        if not csv_reader.fieldnames:
            errors.append(
                ValidationError(
                    row_number=0,
                    error="Empty CSV file",
                ),
            )
            return valid_transactions, errors, 0

        missing_headers = required_headers - set(csv_reader.fieldnames)
        if missing_headers:
            errors.append(
                ValidationError(
                    row_number=0,
                    error=f"Missing required headers: {', '.join(missing_headers)}",
                ),
            )
            return valid_transactions, errors, 0

        # Process rows
        total_rows = 0
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is 1)
            total_rows += 1

            try:
                # Validate row data
                validated_row = TransactionCSVRow(**row)

                # Check if transaction already exists
                exists = await self.transaction_repo.exists(validated_row.transaction_id)
                if exists:
                    errors.append(
                        ValidationError(
                            row_number=row_num,
                            field="transaction_id",
                            error=f"Transaction {validated_row.transaction_id} already exists",
                            raw_data=row,
                        ),
                    )
                    continue

                # Convert to internal schema
                transaction_create = TransactionCreate(**validated_row.model_dump())
                valid_transactions.append(transaction_create)

            except Exception as e:
                # Log validation error
                field = None
                if hasattr(e, "loc") and e.loc:
                    field = str(e.loc[0])

                errors.append(
                    ValidationError(
                        row_number=row_num,
                        field=field,
                        error=str(e),
                        raw_data=row,
                    ),
                )

        return valid_transactions, errors, total_rows

    async def _process_transactions(
        self,
        transactions: list[TransactionCreate],
    ) -> None:
        """Process valid transactions efficiently."""
        # Extract unique customer and product IDs
        customer_ids = {t.customer_id for t in transactions}
        product_ids = {t.product_id for t in transactions}

        # Bulk create/get customers and products
        await self.customer_repo.get_or_create_bulk(customer_ids)
        await self.product_repo.get_or_create_bulk(product_ids)

        # Bulk create transactions
        await self.transaction_repo.create_bulk(transactions)


class ReportService:
    """Service for generating reports."""

    def __init__(
        self,
        transaction_repo: TransactionRepository,
        customer_repo: CustomerRepository,
        product_repo: ProductRepository,
    ) -> None:
        """Initialize service with repositories."""
        self.transaction_repo = transaction_repo
        self.customer_repo = customer_repo
        self.product_repo = product_repo

    async def get_customer_summary(
        self,
        customer_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> CustomerSummaryResponse | None:
        """Generate customer summary report."""
        # Check if customer exists
        exists = await self.customer_repo.exists(customer_id)
        if not exists:
            return None

        # Get aggregated data
        summary_data = await self.transaction_repo.get_customer_summary(
            customer_id=customer_id,
            start_date=start_date,
            end_date=end_date,
        )

        return CustomerSummaryResponse(**summary_data)

    async def get_product_summary(
        self,
        product_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ProductSummaryResponse | None:
        """Generate product summary report."""
        # Check if product exists
        exists = await self.product_repo.exists(product_id)
        if not exists:
            return None

        # Get aggregated data
        summary_data = await self.transaction_repo.get_product_summary(
            product_id=product_id,
            start_date=start_date,
            end_date=end_date,
        )

        return ProductSummaryResponse(**summary_data)

    def convert_to_pln(self, amount: Decimal, currency: CurrencyEnum) -> Decimal:
        """Convert amount to PLN using fixed exchange rates."""
        rate = EXCHANGE_RATES.get(currency, Decimal("1.0"))
        return (amount * rate).quantize(Decimal("0.01"))


class AuthService:
    """Service for handling authentication."""
    
    def __init__(self) -> None:
        """Initialize auth service."""
        self._valid_tokens: set[str] = {settings.API_TOKEN}  # In production, use database
    
    def verify_token(self, token: str) -> bool:
        """
        Verify if token is valid.
        
        Args:
            token: Token to verify
            
        Returns:
            True if token is valid
        """
        if not settings.REQUIRE_AUTH:
            return True
        
        # In production, check against database with expiration
        return token in self._valid_tokens
    
    def authenticate_user(self, provided_token: str) -> str | None:
        """
        Authenticate user with provided token.
        
        Args:
            provided_token: Token provided by user
            
        Returns:
            API token if authentication successful, None otherwise
        """
        # In production, implement proper authentication logic
        # This is a simple demo implementation
        if provided_token == settings.SECRET_KEY:
            return settings.API_TOKEN
        return None
    
    def generate_token(self) -> str:
        """
        Generate a new API token.
        
        Returns:
            New token string
        """
        # In production, store in database with expiration
        token = secrets.token_urlsafe(32)
        self._valid_tokens.add(token)
        return token
