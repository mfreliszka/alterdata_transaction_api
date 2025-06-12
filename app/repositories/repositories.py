"""Repository implementations for data access layer."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, case,distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Customer, ImportBatch, Product, Transaction
from app.schemas.schemas import CurrencyEnum, TransactionCreate


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.session = session


class TransactionRepository(BaseRepository):
    """Repository for transaction operations."""
    
    async def create(self, transaction_data: TransactionCreate) -> Transaction:
        """Create a new transaction."""
        transaction = Transaction(**transaction_data.model_dump())
        self.session.add(transaction)
        await self.session.flush()
        return transaction
    
    async def create_bulk(self, transactions_data: list[TransactionCreate]) -> list[Transaction]:
        """Create multiple transactions in bulk."""
        transactions = [
            Transaction(**data.model_dump()) 
            for data in transactions_data
        ]
        self.session.add_all(transactions)
        await self.session.flush()
        return transactions
    
    async def get_by_id(self, transaction_id: UUID) -> Optional[Transaction]:
        """Get transaction by ID with related data."""
        stmt = (
            select(Transaction)
            .where(Transaction.transaction_id == transaction_id)
            .options(
                selectinload(Transaction.customer),
                selectinload(Transaction.product)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_paginated(
        self,
        *,
        customer_id: Optional[UUID] = None,
        product_id: Optional[UUID] = None,
        offset: int = 0,
        limit: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> tuple[list[Transaction], int]:
        """Get paginated transactions with optional filters."""
        # Build base query
        conditions = []
        
        if customer_id:
            conditions.append(Transaction.customer_id == customer_id)
        if product_id:
            conditions.append(Transaction.product_id == product_id)
        if start_date:
            conditions.append(Transaction.timestamp >= start_date)
        if end_date:
            conditions.append(Transaction.timestamp <= end_date)
        
        # Count query
        count_stmt = select(func.count()).select_from(Transaction)
        if conditions:
            count_stmt = count_stmt.where(and_(*conditions))
        
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # Data query with pagination
        data_stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.customer),
                selectinload(Transaction.product)
            )
            .order_by(Transaction.timestamp.desc())
            .offset(offset)
            .limit(limit)
        )
        
        if conditions:
            data_stmt = data_stmt.where(and_(*conditions))
        
        result = await self.session.execute(data_stmt)
        transactions = list(result.scalars().all())
        
        return transactions, total
    
    async def get_customer_summary(
        self,
        customer_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, any]:
        """Get customer transaction summary."""
        conditions = [Transaction.customer_id == customer_id]
        
        if start_date:
            conditions.append(Transaction.timestamp >= start_date)
        if end_date:
            conditions.append(Transaction.timestamp <= end_date)
        
        # Build aggregation query
        stmt = (
            select(
                func.sum(
                    Transaction.amount * 
                    case(
                        (Transaction.currency == CurrencyEnum.PLN, Decimal("1.0")),
                        (Transaction.currency == CurrencyEnum.EUR, Decimal("4.3")),
                        (Transaction.currency == CurrencyEnum.USD, Decimal("4.0")),
                        else_=Decimal("1.0")
                    )
                ).label("total_amount_pln"),
                func.count(distinct(Transaction.product_id)).label("unique_products_count"),
                func.max(Transaction.timestamp).label("last_transaction_date")
            )
            .where(and_(*conditions))
        )
        
        result = await self.session.execute(stmt)
        row = result.one()

        # Properly format monetary value to 2 decimal places
        total_amount = Decimal(str(row.total_amount_pln or 0))
        total_amount_formatted = total_amount.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return {
            "customer_id": customer_id,
            "total_amount_pln": total_amount_formatted,
            "unique_products_count": row.unique_products_count or 0,
            "last_transaction_date": row.last_transaction_date,
        }
    
    async def get_product_summary(
        self,
        product_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, any]:
        """Get product transaction summary."""
        conditions = [Transaction.product_id == product_id]
        
        if start_date:
            conditions.append(Transaction.timestamp >= start_date)
        if end_date:
            conditions.append(Transaction.timestamp <= end_date)
        
        # Build aggregation query
        stmt = (
            select(
                func.sum(Transaction.quantity).label("total_quantity_sold"),
                func.sum(
                    Transaction.amount * 
                    case(
                        (Transaction.currency == CurrencyEnum.PLN, Decimal("1.0")),
                        (Transaction.currency == CurrencyEnum.EUR, Decimal("4.3")),
                        (Transaction.currency == CurrencyEnum.USD, Decimal("4.0")),
                        else_=Decimal("1.0")
                    )
                ).label("total_revenue_pln"),
                func.count(distinct(Transaction.customer_id)).label("unique_customers_count")
            )
            .where(and_(*conditions))
        )
        
        result = await self.session.execute(stmt)
        row = result.one()

        # Properly format monetary value to 2 decimal places
        total_revenue = Decimal(str(row.total_revenue_pln or 0))
        total_revenue_formatted = total_revenue.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return {
            "product_id": product_id,
            "total_quantity_sold": row.total_quantity_sold or 0,
            "total_revenue_pln": total_revenue_formatted,
            "unique_customers_count": row.unique_customers_count or 0,
        }
    
    async def exists(self, transaction_id: UUID) -> bool:
        """Check if transaction exists."""
        stmt = select(
            select(Transaction.transaction_id)
            .where(Transaction.transaction_id == transaction_id)
            .exists()
        )
        result = await self.session.execute(stmt)
        return result.scalar() or False


class CustomerRepository(BaseRepository):
    """Repository for customer operations."""
    
    async def get_or_create(self, customer_id: UUID) -> Customer:
        """Get existing customer or create new one."""
        stmt = select(Customer).where(Customer.customer_id == customer_id)
        result = await self.session.execute(stmt)
        customer = result.scalar_one_or_none()
        
        if not customer:
            customer = Customer(customer_id=customer_id)
            self.session.add(customer)
            await self.session.flush()
        
        return customer
    
    async def get_or_create_bulk(self, customer_ids: set[UUID]) -> dict[UUID, Customer]:
        """Get or create multiple customers efficiently."""
        # Get existing customers
        stmt = select(Customer).where(Customer.customer_id.in_(customer_ids))
        result = await self.session.execute(stmt)
        existing_customers = {c.customer_id: c for c in result.scalars()}
        
        # Create missing customers
        missing_ids = customer_ids - set(existing_customers.keys())
        if missing_ids:
            new_customers = [Customer(customer_id=cid) for cid in missing_ids]
            self.session.add_all(new_customers)
            await self.session.flush()
            
            # Add to result dict
            for customer in new_customers:
                existing_customers[customer.customer_id] = customer
        
        return existing_customers
    
    async def exists(self, customer_id: UUID) -> bool:
        """Check if customer exists."""
        stmt = select(
            select(Customer.customer_id)
            .where(Customer.customer_id == customer_id)
            .exists()
        )
        result = await self.session.execute(stmt)
        return result.scalar() or False


class ProductRepository(BaseRepository):
    """Repository for product operations."""
    
    async def get_or_create(self, product_id: UUID) -> Product:
        """Get existing product or create new one."""
        stmt = select(Product).where(Product.product_id == product_id)
        result = await self.session.execute(stmt)
        product = result.scalar_one_or_none()
        
        if not product:
            product = Product(product_id=product_id)
            self.session.add(product)
            await self.session.flush()
        
        return product
    
    async def get_or_create_bulk(self, product_ids: set[UUID]) -> dict[UUID, Product]:
        """Get or create multiple products efficiently."""
        # Get existing products
        stmt = select(Product).where(Product.product_id.in_(product_ids))
        result = await self.session.execute(stmt)
        existing_products = {p.product_id: p for p in result.scalars()}
        
        # Create missing products
        missing_ids = product_ids - set(existing_products.keys())
        if missing_ids:
            new_products = [Product(product_id=pid) for pid in missing_ids]
            self.session.add_all(new_products)
            await self.session.flush()
            
            # Add to result dict
            for product in new_products:
                existing_products[product.product_id] = product
        
        return existing_products
    
    async def exists(self, product_id: UUID) -> bool:
        """Check if product exists."""
        stmt = select(
            select(Product.product_id)
            .where(Product.product_id == product_id)
            .exists()
        )
        result = await self.session.execute(stmt)
        return result.scalar() or False


class ImportBatchRepository(BaseRepository):
    """Repository for import batch operations (bonus feature)."""
    
    async def create(
        self,
        filename: str,
        total_rows: int = 0,
    ) -> ImportBatch:
        """Create new import batch."""
        batch = ImportBatch(
            filename=filename,
            total_rows=total_rows,
            status="pending",
        )
        self.session.add(batch)
        await self.session.flush()
        return batch
    
    async def update_status(
        self,
        batch_id: UUID,
        status: str,
        processed_rows: Optional[int] = None,
        error_rows: Optional[int] = None,
        error_details: Optional[str] = None,
    ) -> Optional[ImportBatch]:
        """Update import batch status."""
        stmt = select(ImportBatch).where(ImportBatch.batch_id == batch_id)
        result = await self.session.execute(stmt)
        batch = result.scalar_one_or_none()
        
        if batch:
            batch.status = status
            if processed_rows is not None:
                batch.processed_rows = processed_rows
            if error_rows is not None:
                batch.error_rows = error_rows
            if error_details is not None:
                batch.error_details = error_details
            
            await self.session.flush()
        
        return batch
    
    async def get_by_id(self, batch_id: UUID) -> Optional[ImportBatch]:
        """Get import batch by ID."""
        stmt = select(ImportBatch).where(ImportBatch.batch_id == batch_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()