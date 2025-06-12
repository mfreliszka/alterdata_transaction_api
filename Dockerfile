FROM python:3.10-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project definition file
COPY pyproject.toml .

# Install dependencies using uv with --system flag to install without venv
RUN uv pip install --system -e .

# Copy source code
COPY . .

# Run database migrations and start the application
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000