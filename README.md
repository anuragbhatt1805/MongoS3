# MongoDB to S3 Backup Container (MongoS3)

## Description

An ultra-lightweight, production-ready, one-shot Docker container that creates a compressed `mongodump` archive of any MongoDB database, authorizes AWS credentials, streams the backup to Amazon S3 (or any S3-compatible storage), verifies object integrity, cleans up temporary local files, and exits cleanly.

---

## Features

- **Ultra-Slim Footprint:** Built on `python:3.14-alpine` with an uncompressed disk usage of **117 MB** and a download size of **~28 MB**.
- **Native MongoDB Tools:** Uses native `mongodump` with `--archive` and `--gzip` compression for single-stream archives.
- **AWS Pre-flight Verification:** Validates credentials via AWS STS `get_caller_identity` and tests target bucket accessibility via `head_bucket`.
- **High-Performance Upload:** Implements Boto3 multipart transfer with configurable concurrency and real-time upload progress reporting.
- **Remote Verification:** Verifies uploaded objects with S3 `head_object` to ensure size and ETag integrity.
- **Credential Privacy:** Connection string credentials are automatically sanitized and masked in logs.
- **Security First:** Runs as an unprivileged, non-root user (`appuser`, UID `10001`).
- **Clean One-Shot Lifecycle:** Automatically purges temporary files and exits with status `0` on success.
- **S3 Compatibility:** Works with AWS S3, MinIO, Cloudflare R2, Backblaze B2, and LocalStack.

---

## Architecture

For the complete architectural design, data flow diagram, and execution lifecycle, see:
👉 [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Installation

### Pull from Docker Hub

```bash
docker pull anuragbhatt1805/mongo-s3-backup:latest
```

### Or Build Locally

```bash
git clone https://github.com/anuragbhatt1805/MongoS3.git
cd MongoS3
docker build -t mongo-s3-backup:latest .
```

---

## Setup & Deployment (Docker)

### 1. Configure Environment Variables

Create a `.env` file (or provide variables via your orchestrator):

```ini
# Required
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/dbname
S3_BUCKET=my-database-backups

# Optional AWS Credentials (omit if using IAM Roles / IRSA / ECS Task Roles)
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1

# Optional S3 Settings
S3_PREFIX=backups/production
S3_STORAGE_CLASS=STANDARD

# Optional Custom S3 Endpoint (for MinIO, Cloudflare R2, etc.)
# S3_ENDPOINT_URL=http://minio:9000
```

### 2. Run via Docker

```bash
docker run --rm --env-file .env anuragbhatt1805/mongo-s3-backup:latest
```

### 3. Run via Docker Compose

```yaml
version: "3.8"

services:
  backup:
    image: anuragbhatt1805/mongo-s3-backup:latest
    env_file: .env
```

```bash
docker compose run --rm backup
```

---

## License

MIT
