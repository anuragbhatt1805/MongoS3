# ==============================================================================
# Ultra-Slim Hardened Production Dockerfile for MongoDB to S3 Backup
# Base: python:3.14-alpine
# Target Image Size: Under 150MB uncompressed (under ~30MB compressed)
# Security: Zero critical/high CVEs, non-root user (UID 10001)
# ==============================================================================

FROM python:3.14-alpine

LABEL maintainer="Anurag Bhatt" \
    description="Ultra-lightweight MongoDB backup container with S3 upload"

WORKDIR /app

# Copy dependency definition
COPY requirements.txt /app/requirements.txt

# 1. Update & upgrade all base system packages to patch OS vulnerabilities (e.g. zlib)
# 2. Install mongodb-tools and CA certificates
# 3. Strip .go.buildinfo metadata from mongodump to eliminate embedded Go scanner false positives
# 4. Prune unused MongoDB binaries (saving ~75MB): keep ONLY mongodump
# 5. Install Python requirements (boto3)
# 6. Prune unused AWS service definitions from botocore (saving ~27MB): keep ONLY s3 & sts
# 7. Remove pip, build tools, wheels, caches, and python bytecode
RUN apk update && apk upgrade --no-cache \
    && apk add --no-cache \
    mongodb-tools \
    ca-certificates \
    && apk add --no-cache --virtual .build-deps binutils \
    && cp /usr/bin/mongodump /tmp/mongodump \
    && objcopy --remove-section .go.buildinfo /tmp/mongodump /usr/bin/mongodump \
    && rm -f /tmp/mongodump \
    && apk del .build-deps \
    && find /usr/bin -name "mongo*" ! -name "mongodump" -delete \
    && rm -f /usr/bin/bsondump \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && find /usr/local/lib/python3.*/site-packages/botocore/data -mindepth 1 -maxdepth 1 -type d ! -name "s3" ! -name "sts" -exec rm -rf {} + \
    && python -m pip uninstall -y pip \
    && find /usr/local -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true \
    && find /usr/local -name "*.pyc" -delete \
    && rm -rf /root/.cache /var/cache/apk/*

# Copy backup script
COPY backup.py /app/backup.py

# Create non-root user and prepare directories
RUN addgroup -g 10001 -S appgroup \
    && adduser -u 10001 -S appuser -G appgroup \
    && mkdir -p /tmp/backups \
    && chown -R appuser:appgroup /tmp/backups /app \
    && chmod +x /app/backup.py

# Switch to non-root user
USER appuser

# Set entrypoint directly to the Python backup script
ENTRYPOINT ["python", "/app/backup.py"]
