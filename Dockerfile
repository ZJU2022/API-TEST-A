FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Newman and reporter
RUN npm install -g newman newman-reporter-htmlextra

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs reports postman_collections

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Set entrypoint
ENTRYPOINT ["python", "-m", "src.main"]

# Default command (can be overridden)
CMD ["--help"]
