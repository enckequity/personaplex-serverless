# PersonaPlex Serverless Worker for RunPod
# Based on NVIDIA's official setup

ARG BASE_IMAGE="nvcr.io/nvidia/cuda"
ARG BASE_IMAGE_TAG="12.4.1-runtime-ubuntu22.04"

FROM ${BASE_IMAGE}:${BASE_IMAGE_TAG}

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libopus-dev \
    git \
    curl \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Clone PersonaPlex
RUN git clone https://github.com/NVIDIA/personaplex.git /app/personaplex

# Set up Python environment
RUN uv venv /app/.venv --python 3.12
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV="/app/.venv"

# Install PersonaPlex and dependencies
RUN uv pip install /app/personaplex/moshi/. runpod

# Create directories
RUN mkdir -p /app/ssl /app/voices

# Copy our handler
COPY rp_handler.py /app/rp_handler.py

# HuggingFace token will be set via environment variable
ENV HF_TOKEN=""

# Cache directory for model weights (can be mounted to network volume)
ENV HF_HOME="/runpod-volume/.cache/huggingface"
ENV TRANSFORMERS_CACHE="/runpod-volume/.cache/huggingface"

# Expose WebSocket port
EXPOSE 8998

# Run handler
CMD ["python", "-u", "/app/rp_handler.py"]
