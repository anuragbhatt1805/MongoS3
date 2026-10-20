# 🍃 MongoDB to S3 Backup Container (MongoS3)

[![Docker](https://img.shields.io/badge/Docker-python:3.14--alpine-blue.svg)](https://hub.docker.com/_/python)
[![Disk Usage](https://img.shields.io/badge/Disk%20Usage-117MB-brightgreen.svg)](#features)
[![Download Size](https://img.shields.io/badge/Download%20Size-~28MB-brightgreen.svg)](#features)
[![MongoDB Tools](https://img.shields.io/badge/mongodump-100.14-green.svg)](https://www.mongodb.com/docs/database-tools/)
[![AWS SDK](https://img.shields.io/badge/AWS%20SDK-boto3-orange.svg)](https://boto3.amazonaws.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📖 Description

An ultra-lightweight, production-grade, one-shot Docker container that creates a compressed `mongodump` archive of any MongoDB instance, validates AWS credentials, streams the backup to Amazon S3 (or any S3-compatible store), verifies the upload, cleans up local temporary files, and exits cleanly.

---

## ⚡ Features

- 🪶 **Ultra-Slim Footprint:** Built on `python:3.14-alpine` with an uncompressed disk usage of **117 MB** and a compressed download size of only **~28 MB**.
- 🚀 **High Speed & Low I/O:** Streams `mongodump --archive --gzip` directly into a single compressed archive, eliminating disk write amplification and file thrashing.
- ⚡ **Multi-Threaded Uploads:** Leverages Boto3 multipart chunking (8 MB chunks, 10 concurrent threads) with real-time transfer rate (MB/s) tracking.
- ⏱️ **Instant Cold Starts:** Boots and initiates backups in under 0.5s, ideal for serverless, CronJobs, and on-demand container tasks.
- 🔒 **Security Hardened (Non-Root):** Runs strictly as unprivileged `appuser` (`UID 10001`, `GID 10001`) with an isolated temporary workspace.
- 🛡️ **Credential Redaction:** Automatically parses and masks passwords in connection strings from logs, preventing secret leaks.
- 🔍 **Pre-Flight Security Audit:** Validates credentials via AWS STS `get_caller_identity` and logs Caller ARN, Account ID, and UserId before dumping.
- 🧹 **Zero Residual Remnants:** Enforces deterministic file purging in `finally` blocks, guaranteeing zero leftover archives on success or abort.
- ✅ **Remote Byte Verification:** Calls S3 `head_object` to confirm object existence, assert ContentLength matches, and verify ETag integrity.
- 📊 **Structured Observability:** Standardized UTC timestamped logs with real-time percentage and throughput metrics.
- 🌐 **Broad Compatibility:** Works with MongoDB 4.4 through 7.0+, Atlas SRV clusters, AWS S3, MinIO, Cloudflare R2, Backblaze B2, and LocalStack.
- 🎯 **Clean One-Shot Lifecycle:** Deterministic Unix exit codes (`0` on verified success, `1` on error) for seamless monitoring integration.

---

## 🏗️ Architecture

For the complete architectural design, data flow diagram, and step-by-step execution lifecycle, see:
👉 [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 📦 Installation, Setup & Deployment

For quick start, Docker CLI and Docker Compose setups, and the full environment variable reference, see:
👉 [INSTALLATION.md](INSTALLATION.md)

### Quick Pull

```bash
docker pull anuragbhatt1805/mongos3:latest
```

---

## 📄 License

This project is open-source and licensed under the terms of the [MIT License](LICENSE).
