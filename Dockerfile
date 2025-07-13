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
RUN curl -fsSL https://get.docker.com | sh

# Create app directory
WORKDIR /app

# Create log directory
RUN mkdir -p /var/log/docker-revp

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/

# Copy version file
COPY VERSION ./

# Create SSH directory
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Set version environment variables
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