FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    # Playwright/Chromium dependencies
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user early
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app

# Switch to non-root user for pip install
USER appuser

# Install Python dependencies
COPY --chown=appuser:appuser backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Install Playwright chromium browser (as appuser)
RUN /home/appuser/.local/bin/playwright install chromium

# Copy application code
COPY --chown=appuser:appuser backend/app ./app
COPY --chown=appuser:appuser backend/alembic ./alembic
COPY --chown=appuser:appuser backend/alembic.ini .

# Add local bin to PATH for running installed packages
ENV PATH="/home/appuser/.local/bin:$PATH"

# Expose port
EXPOSE 8000

# Run the application
CMD ["/bin/sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
