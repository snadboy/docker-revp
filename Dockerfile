FROM python:3.11-slim

# Version and build arguments
ARG VERSION=unknown
ARG BUILD_DATE
ARG GIT_COMMIT

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssh-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Docker CLI
RUN apt-get update && apt-get install -y \
    ca-certificates \
    gnupg \
    lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create log directory with proper permissions
RUN mkdir -p /var/log/docker-revp && chown 1000:1000 /var/log/docker-revp

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Copy version and changelog files
COPY VERSION ./
COPY CHANGELOG.md ./

# Create user and SSH directory
RUN useradd -u 1000 -m -s /bin/bash app && \
    mkdir -p /home/app/.ssh && \
    chmod 700 /home/app/.ssh && \
    chown 1000:1000 /home/app/.ssh

# Set environment variables
ENV HOME=/home/app
ENV APP_VERSION=${VERSION}
ENV BUILD_DATE=${BUILD_DATE}
ENV GIT_COMMIT=${GIT_COMMIT}

# Add image labels
LABEL version=${VERSION}
LABEL build-date=${BUILD_DATE}
LABEL git-commit=${GIT_COMMIT}
LABEL org.opencontainers.image.version=${VERSION}
LABEL org.opencontainers.image.created=${BUILD_DATE}
LABEL org.opencontainers.image.revision=${GIT_COMMIT}
LABEL org.opencontainers.image.title="Docker Reverse Proxy"
LABEL org.opencontainers.image.description="Docker container monitoring with Caddy reverse proxy integration"

# Expose API port
EXPOSE 8080

# Run the application
CMD ["python", "-m", "src.main"]