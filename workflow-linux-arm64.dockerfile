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

# Install uv via its installer, not COPY --from=ghcr.io/astral-sh/uv:
# this Dockerfile also builds linux/arm/v7, which the uv image has no
# manifest for. The installer resolves the right binary per target arch.
ENV UV_INSTALL_DIR=/usr/local/bin
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Set the working directory
WORKDIR /app

# Copy project files into the container
COPY . .

# Install Python dependencies + PyInstaller via uv
RUN uv sync --frozen && uv pip install pyinstaller

# Update app tables in README before bundling
RUN uv run python scripts/update_tables.py

# Defence in depth: the PyInstaller --add-data below bundles config/
# wholesale, so any local user state copied in by `COPY . .` would ship
# inside the binary (credentials encrypted with the builder's key -
# unusable elsewhere and a privacy leak).
RUN rm -f config/user-config.json config/.dashboard.pid config/.dashboard.owner

# Build the project using PyInstaller at image build time (not CMD)
# so that failures are caught during `docker build` instead of silently at runtime.
# Single-file build: asset naming and self-update logic
# (money4band/updater.py) rely on one binary per platform.
RUN uv run pyinstaller --onefile \
    --name Money4Band \
    main.py \
    --hidden-import colorama \
    --hidden-import docker \
    --hidden-import httpx \
    --hidden-import psutil \
    --hidden-import yaml \
    --hidden-import secrets \
    --hidden-import cryptography \
    --hidden-import fastapi \
    --hidden-import uvicorn \
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
    -y

# Default command just copies artifacts (build already done in RUN step)
CMD ["echo", "Build complete - copy artifacts from /app/dist"]
