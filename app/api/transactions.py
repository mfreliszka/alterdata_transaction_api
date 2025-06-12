"""Transaction-related API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.api.dependencies import ImportSvc, RequireAuth, TransactionSvc
from app.schemas.schemas import (
    FileUploadResponse,
    TransactionListParams,
    TransactionListResponse,
    TransactionResponse,
)


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/upload", response_model=FileUploadResponse)
async def upload_transactions(
    file: UploadFile = File(..., description="CSV file with transaction data"),
    import_service: ImportSvc = ImportSvc,
    _: RequireAuth = RequireAuth,
) -> FileUploadResponse:
    """
    Upload and process a CSV file containing transaction data.
    
    Expected CSV format:
    - transaction_id (UUID)
    - timestamp (ISO 8601)
    - amount (decimal)
    - currency (PLN/EUR/USD)
    - customer_id (UUID)
    - product_id (UUID)
    - quantity (integer)
    
    Invalid rows will be reported but won't block processing of valid ones.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )
    
    # Check file size (optional, e.g., 10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 10MB limit",
        )
    
    try:
        # Process the CSV file
        result = await import_service.import_csv(
            file=file.file,
            filename=file.filename,
        )
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process CSV file: {str(e)}",
        )


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    customer_id: Optional[UUID] = Query(None, description="Filter by customer ID"),
    product_id: Optional[UUID] = Query(None, description="Filter by product ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    transaction_service: TransactionSvc = TransactionSvc,
    _: RequireAuth = RequireAuth,
) -> TransactionListResponse:
    """
    Get paginated list of transactions with optional filtering.
    
    - Supports filtering by customer_id and/or product_id
    - Returns paginated results with metadata
    - Sorted by timestamp (newest first)
    """
    params = TransactionListParams(
        customer_id=customer_id,
        product_id=product_id,
        page=page,
        page_size=page_size,
    )
    
    return await transaction_service.list_transactions(params)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: UUID,
    transaction_service: TransactionSvc = TransactionSvc,
    _: RequireAuth = RequireAuth,
) -> TransactionResponse:
    """
    Get details of a specific transaction by ID.
    
    Returns full transaction details including timestamps.
    """
    transaction = await transaction_service.get_transaction(transaction_id)
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found",
        )
    
    return transaction
