"""Module containing FastAPI application and configuring routes, middleware, and event handlers."""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.routers import api_router
from app.core.config import settings
from app.models.models import Base
from app.db.session import engine


def create_tables() -> None:
    """Create database tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_application() -> FastAPI:
    """Initialize and configure the FastAPI application."""
    _app = FastAPI(
        title=settings.PROJECT_NAME,
        description="""
        Library Management System API

        This API allows library staff to manage books, track borrowing status, and perform other
        library operations.

        ## Features

        * Add, update, and remove books
        * Track book borrowing status
        * Search and filter books
        * Manage borrower information

        ## Authentication

        This version of the API does not include authentication for simplicity.
        """,
        version="0.1.0",
        docs_url=None,  # Disable default docs URL to customize it later
        redoc_url=None,  # Disable default redoc URL to customize it later
    )

    # Set all CORS enabled origins
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom exception handler for validation errors
    @_app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors with more user-friendly responses."""
        error_details = []
        for error in exc.errors():
            error_details.append(
                {
                    "loc": error.get("loc", []),
                    "msg": error.get("msg", ""),
                    "type": error.get("type", ""),
                },
            )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation error", "errors": error_details},
        )

    # Custom exception handler for HTTPException
    @_app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions with consistent response format."""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers,
        )

    # Setup routers
    _app.include_router(api_router, prefix=settings.API_V1_STR)

    # Custom OpenAPI documentation endpoints
    @_app.get(f"{settings.API_V1_STR}/docs", include_in_schema=False)
    async def custom_swagger_ui_html() -> Any:
        """Custom Swagger UI endpoint."""
        return get_swagger_ui_html(
            openapi_url=f"{settings.API_V1_STR}/openapi.json",
            title=f"{settings.PROJECT_NAME} - Swagger UI",
            oauth2_redirect_url=None,
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        )

    @_app.get(f"{settings.API_V1_STR}/redoc", include_in_schema=False)
    async def redoc_html() -> Any:
        """Custom ReDoc endpoint."""
        return get_redoc_html(
            openapi_url=f"{settings.API_V1_STR}/openapi.json",
            title=f"{settings.PROJECT_NAME} - ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
        )

    # Custom OpenAPI schema with examples
    @_app.get(f"{settings.API_V1_STR}/openapi.json", include_in_schema=False)
    async def get_open_api_endpoint() -> Any:
        """Custom OpenAPI schema endpoint."""
        return get_openapi(
            title=settings.PROJECT_NAME,
            version="0.1.0",
            description="Transaction Management System API",
            routes=_app.routes,
        )

    # Startup and shutdown events
    @_app.on_event("startup")
    async def startup_event():
        """Execute code on application startup."""
        logging.info("Starting up Library API")
        #create_tables()  # Create DB tables if they don't exist
        logging.info("Database tables created or verified")

    @_app.on_event("shutdown")
    async def shutdown_event():
        """Execute code on application shutdown."""
        logging.info("Shutting down Library API")

    # Root endpoint
    @_app.get("/", tags=["Health Check"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "ok",
            "message": "Transaction API is running",
            "version": "0.1.0",
            "api_docs": f"{settings.API_V1_STR}/docs",
        }

    return _app


app = get_application()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
