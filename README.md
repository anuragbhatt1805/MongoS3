# 🍃 MongoS3: Production MongoDB to S3 Backup Container

[![Docker Pulls](https://img.shields.io/docker/pulls/anuragbhatt1805/mongos3?logo=docker&logoColor=white&color=0088cc)](https://hub.docker.com/r/anuragbhatt1805/mongos3)
[![Image Size](https://img.shields.io/badge/Image%20Size-~28MB%20compressed-success.svg)](https://hub.docker.com/r/anuragbhatt1805/mongos3/tags)
[![Disk Footprint](https://img.shields.io/badge/Disk%20Usage-117MB-brightgreen.svg)](https://hub.docker.com/r/anuragbhatt1805/mongos3/tags)
[![Base Image](https://img.shields.io/badge/Base-python:3.14--alpine-blue.svg)](https://hub.docker.com/_/python)
[![Security Status](https://img.shields.io/badge/Vulnerabilities-0%20CVEs-brightgreen.svg)](#-security-hardening--compliance)
[![Multi-Arch](https://img.shields.io/badge/Arch-linux%2Famd64%20|%20linux%2Farm64-informational.svg)](https://hub.docker.com/r/anuragbhatt1805/mongos3/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/anuragbhatt1805/MongoS3/blob/main/LICENSE)

---

## ⚡ Quick Reference

- **Maintained by:** [Anurag Bhatt](https://github.com/anuragbhatt1805)
- **Where to get help:** [GitHub Issues & Discussions](https://github.com/anuragbhatt1805/MongoS3/issues)
- **Where to file issues:** [https://github.com/anuragbhatt1805/MongoS3/issues](https://github.com/anuragbhatt1805/MongoS3/issues)
- **Source Code:** [https://github.com/anuragbhatt1805/MongoS3](https://github.com/anuragbhatt1805/MongoS3)
- **Supported Architectures:** `linux/amd64`, `linux/arm64` (Apple Silicon & AWS Graviton native)
- **Docker Image Repository:** [`anuragbhatt1805/mongos3`](https://hub.docker.com/r/anuragbhatt1805/mongos3)

---

## 📖 What is MongoS3?

**MongoS3** is an ultra-lightweight, security-hardened, one-shot Docker container engineered to back up MongoDB databases directly to Amazon S3 or any S3-compatible object storage (MinIO, Cloudflare R2, Backblaze B2, Ceph, LocalStack).

Engineered specifically for scheduled CronJobs, Kubernetes, ECS tasks, and automated cloud workflows, MongoS3 streams a single compressed `mongodump` archive directly, executes pre-flight AWS STS security audits, uploads data using multi-threaded Boto3 chunking, performs byte-level remote integrity verification (`head_object`), guarantees deterministic cleanup of temporary scratch space, and terminates with standard POSIX exit codes (`0` on verified success, `1` on error).

### Why MongoS3?

- **Minimal Attack Surface:** Built strictly on `python:3.14-alpine` with all unnecessary binaries, toolchains, package managers (`pip`), and bytecode pruned.
- **Zero Disk Write Amplification:** Streams `mongodump --archive --gzip` directly into a single compressed file, avoiding uncompressed filesystem thrashing.
- **High Throughput:** Multi-threaded chunked S3 multipart upload with real-time transfer speed (MB/s) and percentage progress metrics.
- **Instant Cold Starts:** Boots and initiates dumps in under 0.5s, optimizing resource usage in ephemeral cloud environments.
- **Zero CVEs:** Audited against Aqua Trivy and Docker Scout with zero known vulnerabilities.

---

## 🚀 How to Use This Image

### 1. One-Shot Run (Docker CLI)

Run a backup instantly by providing environment variables directly:

```bash
docker run --rm \
  -e MONGO_URI="mongodb+srv://app_user:YourSecurePassword@cluster0.mongodb.net/production?retryWrites=true&w=majority" \
  -e S3_BUCKET="my-production-backups" \
  -e S3_PREFIX="mongodb/daily" \
  -e AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE" \
  -e AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" \
  -e AWS_REGION="us-east-1" \
  anuragbhatt1805/mongos3:latest
```

### 2. Run with an Environment File (`.env`)

For security and cleaner invocation, define credentials in an environment file:

```ini
# .env
MONGO_URI=mongodb+srv://app_user:YourSecurePassword@cluster0.mongodb.net/production?retryWrites=true&w=majority
S3_BUCKET=my-production-backups
S3_PREFIX=mongodb/daily
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
S3_STORAGE_CLASS=STANDARD_IA
```

Execute with a single flag:

```bash
docker run --rm --env-file .env anuragbhatt1805/mongos3:latest
```

### 3. Docker Compose

Integrate MongoS3 into your existing application stack via `docker-compose.yml`:

```yaml
services:
  mongodb-backup:
    image: anuragbhatt1805/mongos3:latest
    env_file:
      - .env
    restart: "no"
```

Trigger an on-demand backup anytime:

```bash
docker compose run --rm mongodb-backup
```

### 4. Production Orchestration: Kubernetes CronJob

Schedule automated, recurring backups in Kubernetes using IAM Roles for Service Accounts (IRSA) or Kubernetes Secrets:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: mongodb-s3-backup
  namespace: database
spec:
  schedule: "0 2 * * *" # Runs every day at 02:00 UTC
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 5
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: mongos3
              image: anuragbhatt1805/mongos3:latest
              imagePullPolicy: IfNotPresent
              env:
                - name: MONGO_URI
                  valueFrom:
                    secretKeyRef:
                      name: mongodb-credentials
                      key: connection-string
                - name: S3_BUCKET
                  value: "production-mongodb-backups"
                - name: S3_PREFIX
                  value: "cluster-primary"
                - name: AWS_REGION
                  value: "us-east-1"
                - name: S3_STORAGE_CLASS
                  value: "INTELLIGENT_TIERING"
              resources:
                requests:
                  memory: "128Mi"
                  cpu: "100m"
                limits:
                  memory: "512Mi"
                  cpu: "1000m"
```

---

## ⚙️ Configuration & Environment Variables

All parameters can be configured via environment variables or CLI options:

| Environment Variable | CLI Flag | Default | Required | Description |
|---|---|---|---|---|
| `MONGO_URI` / `MONGODB_URI` | `--mongo-uri` | *None* | **Yes** | MongoDB connection string (`mongodb://` or `mongodb+srv://`). Passwords are automatically masked in logs. |
| `S3_BUCKET` | `--s3-bucket` | *None* | **Yes** | Target S3 bucket name. |
| `S3_PREFIX` | `--s3-prefix` | `mongodb-backups` | No | Prefix / subfolder in the bucket (e.g. `backups/daily`). |
| `S3_KEY` | `--s3-key` | *auto-generated* | No | Explicit S3 object key. Defaults to `{prefix}/mongodb_backup_%Y%m%d_%H%M%S.archive.gz`. |
| `AWS_ACCESS_KEY_ID` | *Env only* | *None* | Optional* | AWS Access Key ID (*not required if running with AWS IAM Roles / IRSA / ECS Task Roles). |
| `AWS_SECRET_ACCESS_KEY` | *Env only* | *None* | Optional* | AWS Secret Access Key (*not required if running with AWS IAM Roles / IRSA / ECS Task Roles). |
| `AWS_SESSION_TOKEN` | *Env only* | *None* | No | AWS Temporary Session Token (for STS assumed roles). |
| `AWS_REGION` | `--aws-region` | `us-east-1` | No | AWS target region (e.g., `us-east-1`, `eu-west-1`). |
| `S3_STORAGE_CLASS` | `--storage-class`| `STANDARD` | No | S3 storage tier: `STANDARD`, `STANDARD_IA`, `INTELLIGENT_TIERING`, `GLACIER`. |
| `S3_ENDPOINT_URL` | `--s3-endpoint-url`| *None* | No | Custom S3 endpoint URL for S3-compatible providers (MinIO, R2, LocalStack). |
| `MONGO_DATABASE` | `--database` | *all* | No | Restrict backup to a single specific database. |
| `MONGO_COLLECTION` | `--collection` | *all* | No | Restrict backup to a single specific collection (requires `--database`). |
| `MONGODUMP_EXTRA_ARGS` | `--mongodump-extra-args` | *None* | No | Custom flags passed to `mongodump` (e.g. `--oplog`). |
| `BACKUP_DIR` | `--backup-dir` | `/tmp/backups` | No | Internal scratch directory inside container. |

---

## 🌐 S3-Compatible Storage Compatibility

MongoS3 supports any S3-compliant object store via `S3_ENDPOINT_URL`:

- **Cloudflare R2:** `S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com`
- **MinIO (Self-Hosted):** `S3_ENDPOINT_URL=https://minio.internal.domain:9000`
- **Backblaze B2:** `S3_ENDPOINT_URL=https://s3.<region>.backblazeb2.com`
- **LocalStack / Mock S3:** `S3_ENDPOINT_URL=http://localhost:4566`

---

## 🔒 Security Hardening & Compliance

- **Unprivileged Execution:** Runs strictly under non-root system user `appuser` (`UID 10001`, `GID 10001`).
- **Zero Known CVEs:** Image packages and dependencies are scanned and verified clean against Aqua Trivy and Docker Scout.
- **Sensitive Data Masking:** MongoDB connection string passwords are sanitized using RFC 3986 URL parsing before appearing in any container log.
- **Pre-Flight Authentication Audit:** Calls AWS STS `GetCallerIdentity` at startup to verify and log caller identity (Account ID, ARN, and UserId) before database dumps commence.
- **Guaranteed Cleanup:** Employs deterministic cleanup in `finally` blocks, removing temporary archives regardless of whether the execution succeeded or was interrupted.
- **Remote Byte Verification:** Executes `head_object` against AWS S3 after upload to verify remote Content-Length matches local file size and records the ETag hash.

---

## 🏷️ Image Tags & Architectures

| Tag | Architecture | Description |
|---|---|---|
| `latest` | `amd64`, `arm64` | Latest stable build from `main` branch. |
| `v1.0.<build>` | `amd64`, `arm64` | Semantic build releases. |
| `<git-sha>` | `amd64`, `arm64` | Immutable commit SHA pinning for immutable Infrastructure-as-Code. |

---

## 📚 Deep Dive Documentation

For advanced topics, technical lifecycle diagrams, and comprehensive deployment configurations, refer to the project documentation:

- 🏗️ [**Architecture & Execution Flow**](https://github.com/anuragbhatt1805/MongoS3/blob/main/ARCHITECTURE.md) – Detailed step-by-step lifecycle, sub-process pipe design, and memory bounds.
- 📦 [**Installation & Deployment Guide**](https://github.com/anuragbhatt1805/MongoS3/blob/main/INSTALLATION.md) – Extended setup guides for AWS ECS, AWS Lambda, Kubernetes, and local development.

---

## 📄 License

MongoS3 is open-source software licensed under the terms of the [MIT License](https://github.com/anuragbhatt1805/MongoS3/blob/main/LICENSE).
