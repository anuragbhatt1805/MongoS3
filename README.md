# MongoDB to S3 Backup Docker Container

[![Docker](https://img.shields.io/badge/Docker-python:3.12--alpine-blue.svg)](https://hub.docker.com/_/python)
[![Image Size](https://img.shields.io/badge/Disk%20Usage-115MB-brightgreen.svg)](#features)
[![Download Size](https://img.shields.io/badge/Content%20Size-28MB-brightgreen.svg)](#features)
[![MongoDB Tools](https://img.shields.io/badge/mongodump-100.14-green.svg)](https://www.mongodb.com/docs/database-tools/)
[![Boto3](https://img.shields.io/badge/AWS%20SDK-boto3-orange.svg)](https://boto3.amazonaws.com/)

An ultra-lightweight, production-grade, one-shot Docker container that creates a compressed `mongodump` archive of any MongoDB instance, validates AWS credentials, streams the backup to Amazon S3 (or any S3-compatible store), verifies the upload, cleans up local temporary files, and exits cleanly.

---

## Features

- **Ultra-Lightweight Footprint:** Built on `python:3.12-alpine` with an uncompressed disk usage of **115 MB** and compressed transfer size of **~28 MB** (down from 295 MB).
- **Official Database Tools:** Uses native `mongodump` with `--archive` and `--gzip` compression for minimal I/O and zero multi-file overhead.
- **AWS Credential Authorization:** Validates AWS credentials before dumping via STS `get_caller_identity` and tests destination bucket access via S3 `head_bucket`.
- **High-Performance Upload:** Uses Boto3's `TransferConfig` with multipart chunking and real-time upload progress logging.
- **Remote Verification:** Calls S3 `head_object` to confirm object existence, content length, and ETag before declaring success.
- **Security & Privacy:** 
  - Connection string credentials (passwords) are automatically sanitized in logs.
  - Runs as an unprivileged non-root user (`appuser`, UID `10001`).
- **One-Shot Lifecycle:** Runs the backup, cleans up temporary files from `/tmp/backups`, and immediately exits with `0` (or `1` on error). Ideal for cron jobs and external schedulers.
- **S3-Compatible Storage Support:** Fully compatible with AWS S3, MinIO, Cloudflare R2, Backblaze B2, Ceph, and LocalStack via `S3_ENDPOINT_URL`.

---

## Architecture Flow

```
                      +-----------------------------------+
                      | External Scheduler / docker run   |
                      +-----------------+-----------------+
                                        |
                                        v
                    +---------------------------------------+
                    |  Container: mongo-s3-backup:latest    |
                    |                                       |
                    | 1. Read Environment Variables / CLI   |
                    | 2. Mask URI & Authorize AWS / S3      |
                    +-------------------+-------------------+
                                        |
               +------------------------+------------------------+
               |                                                 |
               v                                                 v
   +-----------------------+                         +-----------------------+
   |   Remote MongoDB      |                         |       AWS S3          |
   | (Atlas / EC2 / Local) |                         | (or S3-compatible)    |
   +-----------+-----------+                         +-----------+-----------+
               |                                                 |
               | [mongodump --archive --gzip]                    |
               v                                                 |
   +-----------------------+                                     |
   | Container /tmp/backup |                                     |
   |  (*.archive.gz)       |                                     |
   +-----------+-----------+                                     |
               |                                                 |
               | [Boto3 Multipart Upload + Progress Callback]    |
               +------------------------------------------------>|
                                                                 |
                                                                 | [Verify S3 head_object]
                                                                 |<-----------------------+
                                                                 |
               +-------------------------------------------------+
               |
               v
   +-----------------------+
   | Clean up /tmp file    |
   | Container exits 0     |
   +-----------------------+
```

---

## File Structure

```
MongoS3/
├── Dockerfile              # Minimal Alpine-based container definition
├── backup.py               # Main Python orchestrator (mongodump + Boto3)
├── requirements.txt        # Python dependencies (boto3, botocore)
├── .env.example            # Environment configuration template
├── .dockerignore           # Excludes local files from image build
├── tests/
│   ├── mock_s3.py          # Standalone S3 mock server for local testing
│   └── run_e2e_test.sh     # Automated end-to-end integration test suite
└── README.md               # Documentation
```

---

## Configuration Reference

Parameters can be provided via **environment variables** or **CLI arguments** (CLI flags override environment variables).

| Environment Variable | CLI Argument | Default | Required | Description |
|---|---|---|---|---|
| `MONGO_URI` / `MONGODB_URI` | `--mongo-uri` | _None_ | **Yes** | MongoDB connection string (e.g., `mongodb://user:pass@host:27017/db` or `mongodb+srv://...`) |
| `S3_BUCKET` | `--s3-bucket` | _None_ | **Yes** | Destination S3 bucket name |
| `S3_PREFIX` | `--s3-prefix` | `mongodb-backups` | No | Folder prefix in S3 (e.g. `backups/production`) |
| `S3_KEY` | `--s3-key` | _auto-generated_ | No | Explicit S3 object key (overrides auto-generated timestamp) |
| `AWS_ACCESS_KEY_ID` | _env only_ | _None_ | Optional* | AWS Access Key (*not needed if using IAM roles / IRSA) |
| `AWS_SECRET_ACCESS_KEY` | _env only_ | _None_ | Optional* | AWS Secret Key (*not needed if using IAM roles / IRSA) |
| `AWS_SESSION_TOKEN` | _env only_ | _None_ | No | Temporary AWS session token |
| `AWS_REGION` | `--aws-region` | `us-east-1` | No | AWS Region |
| `S3_STORAGE_CLASS` | `--storage-class` | `STANDARD` | No | S3 class (`STANDARD`, `STANDARD_IA`, `GLACIER`, etc.) |
| `S3_ENDPOINT_URL` | `--s3-endpoint-url`| _None_ | No | Custom S3 endpoint URL (MinIO, LocalStack, Cloudflare R2) |
| `MONGO_DATABASE` | `--database` | _all databases_ | No | Specific database to backup |
| `MONGO_COLLECTION` | `--collection` | _all_ | No | Specific collection to backup |
| `MONGODUMP_EXTRA_ARGS` | `--mongodump-extra-args` | _None_ | No | Extra flags passed to `mongodump` (e.g., `--oplog`) |
| `BACKUP_DIR` | `--backup-dir` | `/tmp/backups` | No | Local scratch directory inside container |

---

## Quick Start

### 1. Build the Docker Image

```bash
docker build -t mongo-s3-backup:latest .
```

Verify the image size:
```bash
docker images mongo-s3-backup:latest
# Output shows ~80 MB content size
```

### 2. Configure Environment

Copy the template configuration file:
```bash
cp .env.example .env
```

Edit `.env` with your actual MongoDB URI, AWS credentials, and S3 bucket:
```ini
MONGO_URI=mongodb+srv://admin:MySecretPassword@cluster0.abcde.mongodb.net/production?retryWrites=true&w=majority
S3_BUCKET=my-app-database-backups
S3_PREFIX=backups/production
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
S3_STORAGE_CLASS=STANDARD
```

### 3. Run the Backup

```bash
docker run --rm --env-file .env mongo-s3-backup:latest
```

Sample output:
```
2026-10-20 10:23:38 [INFO] === Starting MongoDB to S3 Backup Process ===
2026-10-20 10:23:38 [INFO] Authorizing AWS credentials...
2026-10-20 10:23:38 [INFO] AWS Authorization successful! Account: 123456789012, Arn: arn:aws:iam::123456789012:user/backup-agent
2026-10-20 10:23:38 [INFO] Checking access to S3 bucket: 'my-app-database-backups'...
2026-10-20 10:23:39 [INFO] S3 bucket 'my-app-database-backups' is accessible and verified.
2026-10-20 10:23:39 [INFO] Starting mongodump against: mongodb+srv://admin:****@cluster0.abcde.mongodb.net/production
2026-10-20 10:23:39 [INFO] Target archive destination: /tmp/backups/mongo_dump_all_databases_20261020_102339Z.archive.gz
2026-10-20 10:23:42 [INFO] [mongodump] done dumping production.users (15420 documents)
2026-10-20 10:23:43 [INFO] Dump completed successfully in 4.12s! Archive size: 12.45 MB (13054812 bytes)
2026-10-20 10:23:43 [INFO] Starting upload to s3://my-app-database-backups/backups/production/mongo_dump_all_databases_20261020_102339Z.archive.gz (Storage Class: STANDARD)...
2026-10-20 10:23:45 [INFO] S3 Upload Progress: 100.0% (12.45 MB / 12.45 MB) - Speed: 6.22 MB/s
2026-10-20 10:23:45 [INFO] S3 Upload finished in 2.00s! Average speed: 6.22 MB/s
2026-10-20 10:23:45 [INFO] Verifying uploaded object in S3: s3://my-app-database-backups/backups/production/mongo_dump_all_databases_20261020_102339Z.archive.gz...
2026-10-20 10:23:46 [INFO] Verification PASSED! S3 Object verified: size=13054812 bytes, ETag=4f8b2...
2026-10-20 10:23:46 [INFO] ==================================================
2026-10-20 10:23:46 [INFO] BACKUP COMPLETE & VERIFIED: s3://my-app-database-backups/backups/production/mongo_dump_all_databases_20261020_102339Z.archive.gz
2026-10-20 10:23:46 [INFO] Container task successful. Exiting with status 0.
2026-10-20 10:23:46 [INFO] ==================================================
2026-10-20 10:23:46 [INFO] Cleaned up temporary archive file: /tmp/backups/mongo_dump_all_databases_20261020_102339Z.archive.gz
```

---

## Scheduling & Deployment

### Option A: Host Cron Job (Linux / macOS)

Add this line to `/etc/crontab` or `crontab -e` to run daily at 02:00 UTC:

```bash
0 2 * * * docker run --rm --env-file /etc/mongo-backup.env mongo-s3-backup:latest >> /var/log/mongo-backup.log 2>&1
```

### Option B: Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: mongodb-s3-backup
  namespace: database
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 5
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: backup
              image: your-registry.com/mongo-s3-backup:latest
              env:
                - name: MONGO_URI
                  valueFrom:
                    secretKeyRef:
                      name: mongodb-secrets
                      key: MONGO_URI
                - name: S3_BUCKET
                  value: "my-company-database-backups"
                - name: S3_PREFIX
                  value: "production/mongodb"
                - name: AWS_REGION
                  value: "us-east-1"
                - name: AWS_ACCESS_KEY_ID
                  valueFrom:
                    secretKeyRef:
                      name: aws-s3-backup-credentials
                      key: AWS_ACCESS_KEY_ID
                - name: AWS_SECRET_ACCESS_KEY
                  valueFrom:
                    secretKeyRef:
                      name: aws-s3-backup-credentials
                      key: AWS_SECRET_ACCESS_KEY
```

---

## Restoring from Backup

To restore an archive from S3 into a MongoDB instance:

1. Download the archive from S3:
   ```bash
   aws s3 cp s3://my-app-database-backups/backups/production/mongo_dump_all_databases_20261020_102339Z.archive.gz ./backup.archive.gz
   ```

2. Restore using `mongorestore`:
   ```bash
   # Restore into local or remote MongoDB instance
   mongorestore --uri="mongodb://root:password@localhost:27017" --archive=backup.archive.gz --gzip --drop
   ```
   *(The `--drop` flag removes existing collections before restoring them)*

---

## Local Verification & Testing

An automated test script is provided in `tests/run_e2e_test.sh` that spins up an isolated Docker network, starts a live MongoDB server, seeds test data, launches a mock S3 server, runs the backup container, and verifies the whole pipeline:

```bash
./tests/run_e2e_test.sh
```

## CI/CD: Automated Testing & Docker Hub Publishing

The repository includes a GitHub Actions workflow in [`.github/workflows/docker-publish.yml`](file:///.github/workflows/docker-publish.yml):

1. **Test Stage:** On every push or pull request to `main`, it spins up the container and runs the automated end-to-end integration test suite (`tests/run_e2e_test.sh`).
2. **Publish Stage:** If (and only if) all tests pass on the `main` branch (or release tags `v*.*.*`), it sets up multi-architecture buildx (`linux/amd64` and `linux/arm64`), logs into Docker Hub, and pushes the tagged image:
   - `<username>/mongo-s3-backup:latest`
   - `<username>/mongo-s3-backup:sha-<commit>`
   - `<username>/mongo-s3-backup:<semver>` (on tag release)

### Required GitHub Repository Secrets

Configure the following secrets in your GitHub repository (**Settings** ➔ **Secrets and variables** ➔ **Actions**):

| Secret Name | Description | Example |
|---|---|---|
| `DOCKERHUB_USERNAME` | Your Docker Hub account or organization name | `myorg` or `johndoe` |
| `DOCKERHUB_TOKEN` | Docker Hub Personal Access Token (Read/Write/Delete) | `dckr_pat_...` |

---

## License

MIT
