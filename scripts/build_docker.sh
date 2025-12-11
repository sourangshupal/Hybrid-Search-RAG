#!/bin/bash
# Build script for Hybrid Search RAG Docker image

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="${IMAGE_NAME:-hybrid-rag-api}"
VERSION="${VERSION:-latest}"
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Building Hybrid Search RAG Docker Image${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo -e "Image: ${YELLOW}$IMAGE_NAME:$VERSION${NC}"
echo -e "Build Date: ${YELLOW}$BUILD_DATE${NC}"
echo -e "VCS Ref: ${YELLOW}$VCS_REF${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running${NC}"
    exit 1
fi

# Build image
echo -e "${GREEN}Building Docker image...${NC}"
docker build \
    -f docker/Dockerfile \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg VCS_REF="$VCS_REF" \
    --build-arg VERSION="$VERSION" \
    -t "$IMAGE_NAME:$VERSION" \
    -t "$IMAGE_NAME:latest" \
    .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build successful!${NC}"
else
    echo -e "${RED}✗ Build failed!${NC}"
    exit 1
fi

# Show image info
echo ""
echo -e "${GREEN}Image Information:${NC}"
docker images "$IMAGE_NAME:$VERSION" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Optionally run tests
if [ "$RUN_TESTS" = "true" ]; then
    echo ""
    echo -e "${GREEN}Running tests...${NC}"

    # Start container for testing
    docker run --rm -d \
        --name test-api \
        -p 8000:8000 \
        -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-dummy}" \
        -e OPENAI_API_KEY="${OPENAI_API_KEY:-dummy}" \
        -e COHERE_API_KEY="${COHERE_API_KEY:-dummy}" \
        "$IMAGE_NAME:$VERSION"

    # Wait for container to be healthy
    echo "Waiting for container to be healthy..."
    for i in {1..30}; do
        if [ "$(docker inspect -f '{{.State.Health.Status}}' test-api 2>/dev/null)" = "healthy" ]; then
            echo -e "${GREEN}✓ Container is healthy${NC}"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}✗ Container failed to become healthy${NC}"
            docker logs test-api
            docker stop test-api
            exit 1
        fi
        sleep 2
    done

    # Test health endpoint
    echo "Testing health endpoint..."
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Health check passed${NC}"
    else
        echo -e "${RED}✗ Health check failed${NC}"
        docker logs test-api
        docker stop test-api
        exit 1
    fi

    # Stop test container
    docker stop test-api
    echo -e "${GREEN}✓ All tests passed${NC}"
fi

# Optionally push to registry
if [ "$PUSH_IMAGE" = "true" ]; then
    echo ""
    echo -e "${GREEN}Pushing to registry...${NC}"

    if [ -n "$REGISTRY" ]; then
        docker tag "$IMAGE_NAME:$VERSION" "$REGISTRY/$IMAGE_NAME:$VERSION"
        docker push "$REGISTRY/$IMAGE_NAME:$VERSION"

        if [ "$VERSION" != "latest" ]; then
            docker tag "$IMAGE_NAME:$VERSION" "$REGISTRY/$IMAGE_NAME:latest"
            docker push "$REGISTRY/$IMAGE_NAME:latest"
        fi

        echo -e "${GREEN}✓ Push successful${NC}"
    else
        echo -e "${YELLOW}Warning: REGISTRY not set, skipping push${NC}"
    fi
fi

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Build Complete!${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "To run the image:"
echo "  docker run -p 8000:8000 $IMAGE_NAME:$VERSION"
echo ""
echo "To run with docker-compose:"
echo "  cd docker && docker-compose -f docker-compose.prod.yml up -d"
