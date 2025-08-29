FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    wget \
    git \
    libssl-dev \
    pkg-config \
    build-essential \
    libudev-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Solana CLI
RUN curl -sSfL https://release.solana.com/stable/install | sh
ENV PATH="/root/.local/share/solana/install/active_release/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt

# Initialize IPFS (will be overridden by docker-compose volumes)
RUN wget https://dist.ipfs.tech/kubo/v0.23.0/kubo_v0.23.0_linux-amd64.tar.gz && \
    tar -xzf kubo_v0.23.0_linux-amd64.tar.gz && \
    cd kubo && \
    bash install.sh && \
    ipfs init

# Configure IPFS API
RUN ipfs config Addresses.API /ip4/0.0.0.0/tcp/5001

# Set working directory
WORKDIR /audit

# Copy project files
COPY . .

# Expose ports
EXPOSE 5001 8000

# Default command
CMD ["bash"]
