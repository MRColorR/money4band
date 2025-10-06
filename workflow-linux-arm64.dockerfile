# Use Python 3.12 as the base image
FROM python:3.12

# Set environment variables for non-interactive installation
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary packages
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-setuptools \
    git \
    curl \
    && apt-get clean

# Install PyInstaller
RUN pip install pyinstaller

# Set the working directory
WORKDIR /app

# Copy project files into the container
COPY . .

# Install Python dependencies
RUN pip install -r requirements.txt

# Build the project using PyInstaller
CMD ["pyinstaller", "--onedir", "--name", "Money4Band", "main.py", "--hidden-import", "colorama", "--hidden-import", "docker", "--hidden-import", "requests", "--hidden-import", "pyyaml", "--hidden-import", "psutil", "--hidden-import", "yaml", "--hidden-import", "secrets", "--add-data", ".resources:.resources", "--add-data", "config:config", "--add-data", "utils:utils", "--add-data", "template:template", "--add-data", "LICENSE:LICENSE", "--add-data", "README.md:README.md", "--contents-directory", ".", "-y"]
