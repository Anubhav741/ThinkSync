# ─── TrustOps-Env Production Dockerfile ───
FROM python:3.11-slim

# Set maintainer metadata
LABEL maintainer="TrustOps Engineering <engineering@trustops.ai>"
LABEL version="1.0"
LABEL description="Production-grade OpenEnv Moderation Environment"

# Set environment variables for stability
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_TOKEN="" \
    API_BASE_URL="https://router.huggingface.co/v1" \
    MODEL_NAME="Qwen/Qwen2.5-72B-Instruct" \
    PORT=7860 \
    SERVER_HOST="0.0.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security (Passes HF Spaces safety checks)
RUN useradd -m -u 1000 trustops
USER trustops
ENV PATH="/home/trustops/.local/bin:${PATH}"

# Copy requirements and install
COPY --chown=trustops:trustops requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=trustops:trustops . .

# Expose the dashboard port
EXPOSE 7860

# Default command: run inference for OpenEnv evaluation
# Use "python app.py" if you want to launch the Gradio dashboard instead
CMD ["python", "inference.py"]
