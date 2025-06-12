"""Dependency injection for FastAPI routes."""

from typing import Annotated, AsyncGenerator, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.models import Customer, Product, Transaction
from app.repositories.repositories import (
    CustomerRepository,
    ImportBatchRepository,
    ProductRepository,
    TransactionRepository,
)
from app.services.services import (
    AuthService,
    ImportService,
    ReportService,
    TransactionService,
)


# Database dependency
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting database session.
    
    Yields:
        AsyncSession instance
    """
    async for session in get_db():
        yield session


# Security dependencies
security = HTTPBearer(auto_error=False)

# Authentication dependencies
async def get_auth_service() -> AuthService:
    """Get auth service instance."""
    return AuthService()


async def get_current_token(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> str:
    """
    Validate and get current token from Authorization header.
    
    Args:
        credentials: HTTP Authorization credentials
        auth_service: Auth service instance
        
    Returns:
        Validated token
        
    Raises:
        HTTPException: If authentication fails
    """
    if not settings.REQUIRE_AUTH:
        return "no-auth-required"
    
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    if not auth_service.verify_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token


# Optional authentication (for endpoints that work with or without auth)
async def get_current_token_optional(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> Optional[str]:
    """
    Optionally validate token from Authorization header.
    
    Returns None if no token provided or auth is disabled.
    """
    if not settings.REQUIRE_AUTH:
        return None
    
    if not credentials:
        return None
    
    token = credentials.credentials
    if auth_service.verify_token(token):
        return token
    
    return None

# Repository dependencies
def get_transaction_repository(
    db: AsyncSession = Depends(get_db_session),
) -> TransactionRepository:
    """
    Dependency for getting a TransactionRepository instance.
    
    Args:
        db: Database session
        
    Returns:
        A TransactionRepository instance
    """
    return TransactionRepository(session=db)


def get_customer_repository(
    db: AsyncSession = Depends(get_db_session),
) -> CustomerRepository:
    """
    Dependency for getting a CustomerRepository instance.
    
    Args:
        db: Database session
        
    Returns:
        A CustomerRepository instance
    """
    return CustomerRepository(session=db)


def get_product_repository(
    db: AsyncSession = Depends(get_db_session),
) -> ProductRepository:
    """
    Dependency for getting a ProductRepository instance.
    
    Args:
        db: Database session
        
    Returns:
        A ProductRepository instance
    """
    return ProductRepository(session=db)


def get_import_batch_repository(
    db: AsyncSession = Depends(get_db_session),
) -> ImportBatchRepository:
    """
    Dependency for getting an ImportBatchRepository instance.
    
    Args:
        db: Database session
        
    Returns:
        An ImportBatchRepository instance
    """
    return ImportBatchRepository(session=db)


# Service dependencies
def get_transaction_service(
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
    customer_repo: CustomerRepository = Depends(get_customer_repository),
    product_repo: ProductRepository = Depends(get_product_repository),
) -> TransactionService:
    """
    Dependency for getting a TransactionService instance.
    
    Args:
        transaction_repo: TransactionRepository instance
        customer_repo: CustomerRepository instance
        product_repo: ProductRepository instance
        
    Returns:
        A TransactionService instance
    """
    return TransactionService(
        transaction_repo=transaction_repo,
        customer_repo=customer_repo,
        product_repo=product_repo,
    )


def get_import_service(
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
    customer_repo: CustomerRepository = Depends(get_customer_repository),
    product_repo: ProductRepository = Depends(get_product_repository),
    import_batch_repo: Optional[ImportBatchRepository] = Depends(get_import_batch_repository),
) -> ImportService:
    """
    Dependency for getting an ImportService instance.
    
    Args:
        transaction_repo: TransactionRepository instance
        customer_repo: CustomerRepository instance
        product_repo: ProductRepository instance
        import_batch_repo: Optional ImportBatchRepository instance
        
    Returns:
        An ImportService instance
    """
    return ImportService(
        transaction_repo=transaction_repo,
        customer_repo=customer_repo,
        product_repo=product_repo,
        import_batch_repo=import_batch_repo,
    )


def get_report_service(
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
    customer_repo: CustomerRepository = Depends(get_customer_repository),
    product_repo: ProductRepository = Depends(get_product_repository),
) -> ReportService:
    """
    Dependency for getting a ReportService instance.
    
    Args:
        transaction_repo: TransactionRepository instance
        customer_repo: CustomerRepository instance
        product_repo: ProductRepository instance
        
    Returns:
        A ReportService instance
    """
    return ReportService(
        transaction_repo=transaction_repo,
        customer_repo=customer_repo,
        product_repo=product_repo,
    )


def get_auth_service() -> AuthService:
    """
    Dependency for getting an AuthService instance.
    
    Returns:
        An AuthService instance
    """
    return AuthService(secret_key=settings.SECRET_KEY)


# Combined dependencies
async def get_transaction_by_id(
    transaction_id: UUID,
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
) -> Transaction:
    """
    Dependency for getting a transaction by ID.
    
    Args:
        transaction_id: ID of the transaction to get
        transaction_repo: TransactionRepository instance
        
    Returns:
        The transaction if found
        
    Raises:
        HTTPException: If the transaction is not found
    """
    transaction = await transaction_repo.get_by_id(transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found",
        )
    return transaction


async def get_customer_by_id(
    customer_id: UUID,
    customer_repo: CustomerRepository = Depends(get_customer_repository),
) -> Customer:
    """
    Dependency for getting a customer by ID.
    
    Args:
        customer_id: ID of the customer to get
        customer_repo: CustomerRepository instance
        
    Returns:
        The customer if found
        
    Raises:
        HTTPException: If the customer is not found
    """
    exists = await customer_repo.exists(customer_id)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found",
        )
    # Since we only need to verify existence, get or create
    customer = await customer_repo.get_or_create(customer_id)
    return customer


async def get_product_by_id(
    product_id: UUID,
    product_repo: ProductRepository = Depends(get_product_repository),
) -> Product:
    """
    Dependency for getting a product by ID.
    
    Args:
        product_id: ID of the product to get
        product_repo: ProductRepository instance
        
    Returns:
        The product if found
        
    Raises:
        HTTPException: If the product is not found
    """
    exists = await product_repo.exists(product_id)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    # Since we only need to verify existence, get or create
    product = await product_repo.get_or_create(product_id)
    return product


# Auth dependencies (bonus feature)
async def get_current_token(
    authorization: Annotated[Optional[str], Header()] = None,
    auth_service: AuthService = Depends(get_auth_service),
) -> str:
    """
    Dependency for extracting and validating auth token.
    
    Args:
        authorization: Authorization header value
        auth_service: AuthService instance
        
    Returns:
        The validated token
        
    Raises:
        HTTPException: If token is missing or invalid
    """
    if not settings.REQUIRE_AUTH:
        return "no-auth-required"
    
    token = auth_service.extract_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not auth_service.validate_token(f"Bearer {token}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token


async def require_auth(
    token: str = Depends(get_current_token),
) -> None:
    """
    Dependency to require authentication for protected endpoints.
    
    Args:
        token: Validated token from get_current_token
        
    Raises:
        HTTPException: If authentication fails
    """
    # Token is already validated in get_current_token
    # This dependency just makes it explicit that auth is required
    pass


# Type aliases for cleaner code
DbSession = Annotated[AsyncSession, Depends(get_db_session)]
TransactionRepo = Annotated[TransactionRepository, Depends(get_transaction_repository)]
CustomerRepo = Annotated[CustomerRepository, Depends(get_customer_repository)]
ProductRepo = Annotated[ProductRepository, Depends(get_product_repository)]
ImportBatchRepo = Annotated[ImportBatchRepository, Depends(get_import_batch_repository)]

TransactionSvc = Annotated[TransactionService, Depends(get_transaction_service)]
ImportSvc = Annotated[ImportService, Depends(get_import_service)]
ReportSvc = Annotated[ReportService, Depends(get_report_service)]
# AuthSvc = Annotated[AuthService, Depends(get_auth_service)]

# CurrentToken = Annotated[str, Depends(get_current_token)]
# OptionalToken = Annotated[Optional[str], Depends(get_current_token_optional)]
