# Docker Reverse Proxy - Build Automation
#
# Usage:
#   make build              # Build with auto-detected version
#   make build-dev          # Build development version
#   make build-release      # Build release version  
#   make push               # Push to registry
#   make run                # Run locally
#   make clean              # Clean up

# Variables
VERSION ?= $(shell cat VERSION 2>/dev/null || echo "1.0.0")
GIT_COMMIT ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_TAG ?= $(shell git describe --tags --exact-match 2>/dev/null || echo "")
BUILD_DATE ?= $(shell date -u +'%Y-%m-%dT%H:%M:%SZ')
IMAGE_NAME ?= docker-revp
REGISTRY ?= 

# Determine if this is a release build
ifeq ($(GIT_TAG),)
    BUILD_VERSION = $(VERSION)-dev.$(GIT_COMMIT)
    IS_RELEASE = false
else
    BUILD_VERSION = $(VERSION)
    IS_RELEASE = true
endif

# Docker build arguments
DOCKER_BUILD_ARGS = \
	--build-arg VERSION=$(BUILD_VERSION) \
	--build-arg BUILD_DATE=$(BUILD_DATE) \
	--build-arg GIT_COMMIT=$(GIT_COMMIT)

# Image tags
IMAGE_TAGS = \
	-t $(IMAGE_NAME):$(BUILD_VERSION) \
	-t $(IMAGE_NAME):latest

ifeq ($(IS_RELEASE),true)
    IMAGE_TAGS += -t $(IMAGE_NAME):$(VERSION)
endif

ifneq ($(REGISTRY),)
    REGISTRY_TAGS = $(subst -t ,-t $(REGISTRY)/,$(IMAGE_TAGS))
    IMAGE_TAGS += $(REGISTRY_TAGS)
endif

.PHONY: help
help: ## Show this help message
	@echo "Docker Reverse Proxy - Build Automation"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  %-15s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

.PHONY: version-info
version-info: ## Show version information
	@echo "Version Info:"
	@echo "  Version:      $(BUILD_VERSION)"
	@echo "  Git Commit:   $(GIT_COMMIT)"
	@echo "  Git Tag:      $(GIT_TAG)"
	@echo "  Build Date:   $(BUILD_DATE)"
	@echo "  Is Release:   $(IS_RELEASE)"
	@echo "  Image Name:   $(IMAGE_NAME)"
	@echo "  Registry:     $(REGISTRY)"

.PHONY: build
build: version-info ## Build Docker image with auto-detected version
	@echo "Building $(IMAGE_NAME):$(BUILD_VERSION)..."
	docker build $(DOCKER_BUILD_ARGS) $(IMAGE_TAGS) .
	@echo "Build complete!"

.PHONY: build-dev
build-dev: ## Build development version
	$(MAKE) build VERSION=$(VERSION)-dev.$(GIT_COMMIT)

.PHONY: build-release
build-release: ## Build release version (requires git tag)
	@if [ -z "$(GIT_TAG)" ]; then \
		echo "Error: No git tag found. Create a tag first with: git tag v1.0.0"; \
		exit 1; \
	fi
	$(MAKE) build

.PHONY: push
push: ## Push image to registry
	@if [ -z "$(REGISTRY)" ]; then \
		echo "Error: REGISTRY not set. Use: make push REGISTRY=your-registry.com"; \
		exit 1; \
	fi
	@echo "Pushing to registry $(REGISTRY)..."
	docker push $(REGISTRY)/$(IMAGE_NAME):$(BUILD_VERSION)
	docker push $(REGISTRY)/$(IMAGE_NAME):latest
	@if [ "$(IS_RELEASE)" = "true" ]; then \
		docker push $(REGISTRY)/$(IMAGE_NAME):$(VERSION); \
	fi

.PHONY: run
run: ## Run container locally
	docker run --rm -it \
		-p 8080:8080 \
		-e DOCKER_HOSTS="localhost" \
		-e SSH_USER="$$USER" \
		-e SSH_PRIVATE_KEY="$$(cat ~/.ssh/id_rsa)" \
		$(IMAGE_NAME):$(BUILD_VERSION)

.PHONY: run-compose
run-compose: ## Run with docker-compose
	docker-compose up --build

.PHONY: test
test: ## Run tests (placeholder)
	@echo "Running tests..."
	@echo "No tests configured yet"

.PHONY: lint
lint: ## Run linting
	@echo "Running linting..."
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check src/; \
	else \
		echo "ruff not installed, skipping lint"; \
	fi

.PHONY: clean
clean: ## Clean up Docker images and containers
	@echo "Cleaning up..."
	-docker rmi $(IMAGE_NAME):$(BUILD_VERSION) 2>/dev/null
	-docker rmi $(IMAGE_NAME):latest 2>/dev/null
	-docker system prune -f

.PHONY: clean-all
clean-all: clean ## Clean up everything including volumes
	-docker volume prune -f
	-docker network prune -f

.PHONY: logs
logs: ## Show container logs
	docker-compose logs -f docker-revp

.PHONY: shell
shell: ## Get shell in running container
	docker exec -it docker-revp /bin/bash

# Development helpers
.PHONY: dev-setup
dev-setup: ## Set up development environment
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then \
		echo "Creating .env file..."; \
		echo "DOCKER_HOSTS=localhost" > .env; \
		echo "SSH_USER=$$USER" >> .env; \
		echo "SSH_PRIVATE_KEY=" >> .env; \
		echo "Please edit .env file and add your SSH private key"; \
	fi

.PHONY: release
release: ## Create a new release (requires clean git state)
	@echo "Creating release..."
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: Working directory is not clean"; \
		exit 1; \
	fi
	@echo "Current version: $(VERSION)"
	@read -p "Enter new version (e.g., 1.1.0): " NEW_VERSION; \
	echo "$$NEW_VERSION" > VERSION; \
	git add VERSION; \
	git commit -m "chore: bump version to $$NEW_VERSION"; \
	git tag "v$$NEW_VERSION"; \
	echo "Created tag v$$NEW_VERSION"