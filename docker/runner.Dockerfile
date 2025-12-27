# AutoDev Sandbox Runner
# Secure, isolated environment for test execution

FROM python:3.11-slim

# Security: Create non-root user
RUN useradd -m -s /bin/bash autodev

# Install git for patch application
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER autodev

# Default command
CMD ["bash"]
