# Architecture & Workflow

This document details the internal design and lifecycle of the **MongoS3** backup orchestrator.

---

## 1. High-Level Architecture Flow

```
                      +-----------------------------------+
                      | External Scheduler / docker run   |
                      +-----------------+-----------------+
                                        |
                                        v
                    +---------------------------------------+
                    |  Container: anuragbhatt1805/mongos3:latest |
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

## 2. Step-by-Step Execution Lifecycle

1. **Parameter Validation & URL Masking:**
   - Evaluates mandatory environment variables (`MONGO_URI`, `S3_BUCKET`).
   - Masks sensitive username/password combinations in logs to prevent secret leakage.
2. **AWS Pre-flight Authentication:**
   - Invokes AWS STS `get_caller_identity` to verify active credentials (IAM user, IRSA, or ECS task role).
   - Validates destination S3 bucket reachability using `head_bucket`.
3. **Database Dump Generation:**
   - Executes native `mongodump` directly with `--archive` and `--gzip` flags.
   - Streams dump logs to stdout in real time.
   - Verifies the created archive exists and is non-empty.
4. **S3 Multipart Upload:**
   - Transfers the archive using Boto3 `TransferConfig` with 8MB chunk sizes and concurrent threads.
   - Reports upload percentage, transfer rate, and elapsed time via progress callback.
5. **Post-Upload Verification:**
   - Queries S3 using `head_object` to compare remote `ContentLength` and `ETag` against the local file.
6. **Cleanup & Exit:**
   - Removes the local archive file from `/tmp/backups`.
   - Exits with status `0` upon success or status `1` upon failure.
