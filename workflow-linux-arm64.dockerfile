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

# Install PyInstaller
RUN pip install --no-cache-dir pyinstaller

# Set the working directory
WORKDIR /app

# Copy project files into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Build the project using PyInstaller at image build time (not CMD)
# so that failures are caught during `docker build` instead of silently at runtime.
RUN pyinstaller --onedir \
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
    --add-data "config:config" \
    --add-data "money4band:money4band" \
    --add-data "template:template" \
    --add-data "LICENSE:." \
    --add-data "README.md:." \
    --contents-directory "." \
    -y

# Default command just copies artifacts (build already done in RUN step)
CMD ["echo", "Build complete — copy artifacts from /app/dist"]
