# TrustOps-Env Dockerfile
# Target: 2 vCPUs, 8GB RAM (Hugging Face Spaces)
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_TOKEN="" \
    PORT=7860

# Create non-root user for security
RUN useradd -m -u 1000 trustops
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=trustops:trustops . .

# Switch to non-root user
USER trustops

# Expose Gradio port
EXPOSE 7860

# Resource hints (informational — enforced by HF Spaces runtime)
# CPU: 2 vCPUs | RAM: 8GB

# Run inference (OpenEnv evaluation mode)
CMD ["python", "inference.py"]
