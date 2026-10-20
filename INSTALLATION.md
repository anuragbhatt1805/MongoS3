# Installation, Setup & Deployment

This guide covers installation options, setup instructions, deployment with Docker, and the full configuration reference for **MongoS3**.

---

## 📦 Installation

### Option 1: Pull from Docker Hub

```bash
docker pull anuragbhatt1805/mongos3:latest
```

### Option 2: Build from Source

```bash
git clone https://github.com/anuragbhatt1805/MongoS3.git
cd MongoS3
docker build -t anuragbhatt1805/mongos3:latest .
```

---

## 🚀 Quick Start

Run a one-shot backup using inline environment variables:

```bash
docker run --rm \
  -e MONGO_URI="mongodb+srv://user:password@cluster.mongodb.net/dbname" \
  -e S3_BUCKET="my-backup-bucket" \
  -e S3_PREFIX="backups/production" \
  -e AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE" \
  -e AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" \
  -e AWS_REGION="us-east-1" \
  anuragbhatt1805/mongos3:latest
```

---

## 🛠️ Setup & Deployment (Docker)

### 1. Configure Environment Variables (`.env`)

Create a local `.env` configuration file:

```ini
MONGO_URI=mongodb+srv://backup_user:SuperSecretPassword@prod-cluster.mongodb.net/production?retryWrites=true&w=majority
S3_BUCKET=my-company-database-backups
S3_PREFIX=backups/production
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
S3_STORAGE_CLASS=STANDARD
```

### 2. Run via Docker CLI

```bash
docker run --rm --env-file .env anuragbhatt1805/mongos3:latest
```

### 3. Run via Docker Compose

Define the service in [`docker-compose.yml`](docker-compose.yml):

```yaml
services:
  backup:
    image: anuragbhatt1805/mongos3:latest
    env_file:
      - .env
    restart: "no"
```

Execute on demand:

```bash
docker compose run --rm backup
```

---

## ⚙️ Configuration Reference

All settings can be specified via **Environment Variables** or **CLI Arguments** (CLI arguments take precedence over environment variables).

| Environment Variable | CLI Argument | Default | Required | Description |
|---|---|---|---|---|
| `MONGO_URI` / `MONGODB_URI` | `--mongo-uri` | *None* | **Yes** | MongoDB connection URI (`mongodb://...` or `mongodb+srv://...`) |
| `S3_BUCKET` | `--s3-bucket` | *None* | **Yes** | Target AWS S3 bucket name |
| `S3_PREFIX` | `--s3-prefix` | `mongodb-backups` | No | S3 key prefix/folder (e.g. `backups/daily`) |
| `S3_KEY` | `--s3-key` | *auto-generated* | No | Custom S3 object key (overrides automatic timestamp filename) |
| `AWS_ACCESS_KEY_ID` | *Env only* | *None* | Optional* | AWS Access Key ID (*not required if using IAM Roles / IRSA / ECS Task Roles) |
| `AWS_SECRET_ACCESS_KEY` | *Env only* | *None* | Optional* | AWS Secret Access Key (*not required if using IAM Roles / IRSA / ECS Task Roles) |
| `AWS_SESSION_TOKEN` | *Env only* | *None* | No | AWS Session Token (for temporary STS credentials) |
| `AWS_REGION` | `--aws-region` | `us-east-1` | No | Target AWS region (e.g., `us-east-1`, `eu-west-1`) |
| `S3_STORAGE_CLASS` | `--storage-class` | `STANDARD` | No | Storage tier (`STANDARD`, `STANDARD_IA`, `INTELLIGENT_TIERING`, `GLACIER`) |
| `S3_ENDPOINT_URL` | `--s3-endpoint-url`| *None* | No | Custom S3 endpoint URL (for MinIO, Cloudflare R2, LocalStack) |
| `MONGO_DATABASE` | `--database` | *all* | No | Specific database to dump (dumps all databases if omitted) |
| `MONGO_COLLECTION` | `--collection` | *all* | No | Specific collection to dump (dumps all collections if omitted) |
| `MONGODUMP_EXTRA_ARGS` | `--mongodump-extra-args` | *None* | No | Additional flags passed directly to `mongodump` (e.g., `--oplog`) |
| `BACKUP_DIR` | `--backup-dir` | `/tmp/backups` | No | Internal scratch directory inside container |
