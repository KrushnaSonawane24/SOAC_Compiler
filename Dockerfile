# SOAC Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy backend code
COPY backend/ ./backend/

# Create non-root user
RUN useradd -m -u 1000 soac && chown -R soac:soac /app
USER soac

# Expose port
EXPOSE 8000

# Run API
CMD ["uvicorn", "backend.api:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
