"""Report generation API endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import ReportSvc, RequireAuth
from app.schemas.schemas import CustomerSummaryResponse, ProductSummaryResponse


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/customer-summary/{customer_id}", response_model=CustomerSummaryResponse)
async def get_customer_summary(
    customer_id: UUID,
    start_date: Optional[datetime] = Query(
        None,
        description="Filter transactions from this date (ISO 8601)",
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter transactions until this date (ISO 8601)",
    ),
    report_service: ReportSvc = ReportSvc,
    _: RequireAuth = RequireAuth,
) -> CustomerSummaryResponse:
    """
    Get summary report for a specific customer.
    
    Returns:
    - Total amount spent (converted to PLN)
    - Number of unique products purchased
    - Date of last transaction
    
    Exchange rates: 1 EUR = 4.3 PLN, 1 USD = 4.0 PLN
    """
    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date",
        )
    
    summary = await report_service.get_customer_summary(
        customer_id=customer_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with ID {customer_id} not found",
        )
    
    return summary


@router.get("/product-summary/{product_id}", response_model=ProductSummaryResponse)
async def get_product_summary(
    product_id: UUID,
    start_date: Optional[datetime] = Query(
        None,
        description="Filter transactions from this date (ISO 8601)",
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter transactions until this date (ISO 8601)",
    ),
    report_service: ReportSvc = ReportSvc,
    _: RequireAuth = RequireAuth,
) -> ProductSummaryResponse:
    """
    Get summary report for a specific product.
    
    Returns:
    - Total quantity sold
    - Total revenue generated (converted to PLN)
    - Number of unique customers
    
    Exchange rates: 1 EUR = 4.3 PLN, 1 USD = 4.0 PLN
    """
    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before end_date",
        )
    
    summary = await report_service.get_product_summary(
        product_id=product_id,
        start_date=start_date,
        end_date=end_date,
    )
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID {product_id} not found",
        )
    
    return summary
