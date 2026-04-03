# Use Python 3.13 as the base image (match project requires-python)
FROM python:3.13

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-setuptools \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (matches CI pipeline)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set the working directory
WORKDIR /app

# Copy project files into the container
COPY . .

# Install Python dependencies + PyInstaller via uv
RUN uv sync --frozen && uv pip install pyinstaller

# Update app tables in README before bundling
RUN uv run python scripts/update_tables.py

# Build the project using PyInstaller at image build time (not CMD)
# so that failures are caught during `docker build` instead of silently at runtime.
RUN uv run pyinstaller --onedir \
    --name Money4Band \
    main.py \
    --hidden-import colorama \
    --hidden-import docker \
    --hidden-import requests \
    --hidden-import pyyaml \
    --hidden-import psutil \
    --hidden-import yaml \
    --hidden-import secrets \
    --hidden-import cryptography \
    --hidden-import fastapi \
    --hidden-import uvicorn \
    --hidden-import textual \
    --hidden-import money4band \
    --hidden-import money4band.apps \
    --hidden-import money4band.core \
    --hidden-import money4band.docker \
    --hidden-import money4band.network \
    --hidden-import money4band.system \
    --hidden-import money4band.ui \
    --hidden-import money4band.api \
    --hidden-import money4band.dashboard \
    --hidden-import money4band.resources \
    --add-data "config:config" \
    --add-data "money4band:money4band" \
    --add-data "template:template" \
    --add-data "LICENSE:." \
    --add-data "README.md:." \
    --contents-directory "." \
    -y

# Default command just copies artifacts (build already done in RUN step)
CMD ["echo", "Build complete — copy artifacts from /app/dist"]
