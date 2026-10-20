#!/usr/bin/env python3
"""
MongoDB to S3 Backup Script
============================
Performs a mongodump archive of a MongoDB instance and uploads it directly to Amazon S3
(or any S3-compatible object store) using boto3.

Workflow:
1. Validates configuration and environment variables.
2. Authorizes AWS credentials and verifies S3 bucket access.
3. Executes `mongodump` into a compressed archive (.archive.gz).
4. Verifies the dump file integrity and size.
5. Uploads the archive to S3 with progress tracking.
6. Verifies the uploaded S3 object.
7. Cleans up temporary local files and exits with status 0.
"""

import argparse
import datetime
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("mongo_s3_backup")


def mask_mongo_uri(uri: str) -> str:
    """Mask credentials in MongoDB connection string for safe logging."""
    if not uri:
        return ""
    # Matches ://<user>:<password>@
    return re.sub(r"://([^:@]+):([^@]+)@", r"://\1:****@", uri)


class UploadProgressPercentage:
    """Progress tracker callback for boto3 S3 file upload."""

    def __init__(self, filename: str, total_bytes: int):
        self._filename = filename
        self._total_bytes = total_bytes
        self._seen_so_far = 0
        self._start_time = time.time()
        self._last_log_time = self._start_time
        self._last_percent = -1

    def __call__(self, bytes_amount: int):
        self._seen_so_far += bytes_amount
        percent = (
            (self._seen_so_far / self._total_bytes) * 100
            if self._total_bytes > 0
            else 100
        )
        now = time.time()
        # Log at 0%, 25%, 50%, 75%, 100% or every 5 seconds
        percent_int = int(percent)
        if (
            percent_int in (0, 25, 50, 75, 100) and percent_int != self._last_percent
        ) or (now - self._last_log_time >= 5.0):
            mb_uploaded = self._seen_so_far / (1024 * 1024)
            mb_total = self._total_bytes / (1024 * 1024)
            elapsed = now - self._start_time
            speed = (mb_uploaded / elapsed) if elapsed > 0 else 0
            logger.info(
                f"S3 Upload Progress: {percent:.1f}% ({mb_uploaded:.2f} MB / {mb_total:.2f} MB) - Speed: {speed:.2f} MB/s"
            )
            self._last_log_time = now
            self._last_percent = percent_int


def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments with fallback to environment variables."""
    parser = argparse.ArgumentParser(
        description="Backup MongoDB database to AWS S3 or compatible object storage."
    )
    parser.add_argument(
        "--mongo-uri",
        default=os.getenv("MONGO_URI") or os.getenv("MONGODB_URI"),
        help="MongoDB connection URI (can also be set via MONGO_URI env var)",
    )
    parser.add_argument(
        "--s3-bucket",
        default=os.getenv("S3_BUCKET"),
        help="Target S3 bucket name (can also be set via S3_BUCKET env var)",
    )
    parser.add_argument(
        "--s3-prefix",
        default=os.getenv("S3_PREFIX", "mongodb-backups"),
        help="S3 key prefix/folder (default: 'mongodb-backups')",
    )
    parser.add_argument(
        "--s3-key",
        default=os.getenv("S3_KEY"),
        help="Explicit S3 object key (overrides auto-generated timestamped key)",
    )
    parser.add_argument(
        "--s3-endpoint-url",
        default=os.getenv("S3_ENDPOINT_URL"),
        help="Custom S3 endpoint URL for MinIO, LocalStack, Cloudflare R2, etc.",
    )
    parser.add_argument(
        "--aws-region",
        default=os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        help="AWS region (default: us-east-1 or AWS_REGION env var)",
    )
    parser.add_argument(
        "--storage-class",
        default=os.getenv("S3_STORAGE_CLASS", "STANDARD"),
        help="S3 storage class (STANDARD, STANDARD_IA, GLACIER, etc.)",
    )
    parser.add_argument(
        "--database",
        default=os.getenv("MONGO_DATABASE"),
        help="Specific MongoDB database to dump (optional)",
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("MONGO_COLLECTION"),
        help="Specific MongoDB collection to dump (optional)",
    )
    parser.add_argument(
        "--mongodump-extra-args",
        default=os.getenv("MONGODUMP_EXTRA_ARGS", ""),
        help="Additional arguments passed directly to mongodump (e.g., '--oplog')",
    )
    parser.add_argument(
        "--backup-dir",
        default=os.getenv("BACKUP_DIR", "/tmp/backups"),
        help="Local directory inside container for temporary dump files",
    )
    return parser.parse_args()


def validate_environment(args: argparse.Namespace) -> None:
    """Validate mandatory inputs and tool dependencies."""
    errors = []
    if not args.mongo_uri:
        errors.append("MongoDB URI is required (pass --mongo-uri or set MONGO_URI).")
    if not args.s3_bucket:
        errors.append("S3 bucket name is required (pass --s3-bucket or set S3_BUCKET).")

    # Verify mongodump is installed in PATH
    if not shutil.which("mongodump"):
        errors.append("mongodump executable not found in PATH.")

    if errors:
        for err in errors:
            logger.error(f"Configuration Error: {err}")
        sys.exit(1)


def initialize_aws_clients(args: argparse.Namespace):
    """
    Authorize AWS credentials using boto3.
    Verifies authentication via STS get_caller_identity and tests S3 bucket access.
    """
    logger.info("Authorizing AWS credentials...")

    boto_config = Config(
        region_name=args.aws_region,
        retries={"max_attempts": 5, "mode": "standard"},
    )

    client_kwargs = {
        "config": boto_config,
    }
    if args.s3_endpoint_url:
        client_kwargs["endpoint_url"] = args.s3_endpoint_url
        logger.info(f"Using custom S3 endpoint URL: {args.s3_endpoint_url}")

    # Explicit credentials from env if provided; boto3 will also auto-detect from
    # environment variables, IAM roles, ECS task role, or web identity tokens
    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_session_token = os.getenv("AWS_SESSION_TOKEN")

    if aws_access_key and aws_secret_key:
        client_kwargs["aws_access_key_id"] = aws_access_key
        client_kwargs["aws_secret_access_key"] = aws_secret_key
        if aws_session_token:
            client_kwargs["aws_session_token"] = aws_session_token

    session = boto3.Session(region_name=args.aws_region)

    # 1. Verify STS identity (if not using non-AWS custom endpoint where STS might not exist)
    try:
        sts_client = session.client("sts", **client_kwargs)
        identity = sts_client.get_caller_identity()
        logger.info(
            f"AWS Authorization successful! Account: {identity.get('Account')}, "
            f"Arn: {identity.get('Arn')}, UserId: {identity.get('UserId')}"
        )
    except Exception as e:
        if args.s3_endpoint_url:
            logger.warning(
                f"STS identity check skipped or failed on custom endpoint ({e}). Proceeding to S3 authorization."
            )
        else:
            logger.warning(
                f"STS get_caller_identity warning: {e}. Checking direct S3 authorization..."
            )

    # 2. Initialize S3 client
    s3_client = session.client("s3", **client_kwargs)

    # 3. Verify S3 bucket access
    try:
        logger.info(f"Checking access to S3 bucket: '{args.s3_bucket}'...")
        s3_client.head_bucket(Bucket=args.s3_bucket)
        logger.info(f"S3 bucket '{args.s3_bucket}' is accessible and verified.")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code in ("404", "NoSuchBucket"):
            logger.error(f"S3 bucket '{args.s3_bucket}' does not exist.")
            sys.exit(1)
        elif error_code in ("403", "AccessDenied"):
            logger.error(
                f"Access denied to S3 bucket '{args.s3_bucket}'. Check IAM credentials/policy."
            )
            sys.exit(1)
        else:
            logger.warning(
                f"head_bucket returned code {error_code} ({e}). Upload will be attempted."
            )
    except NoCredentialsError:
        logger.error("No AWS credentials found. Please set AWS_ACCESS_KEY_ID & AWS_SECRET_ACCESS_KEY.")
        sys.exit(1)
    except Exception as e:
        logger.warning(f"Bucket check note: {e}. Continuing...")

    return s3_client


def execute_mongodump(args: argparse.Namespace) -> Path:
    """
    Run `mongodump` with --archive and --gzip to generate a compressed backup file.
    Returns the Path to the generated archive file.
    """
    backup_dir = Path(args.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    db_tag = args.database if args.database else "all_databases"
    filename = f"mongo_dump_{db_tag}_{timestamp}.archive.gz"
    output_path = backup_dir / filename

    cmd = [
        "mongodump",
        f"--uri={args.mongo_uri}",
        f"--archive={str(output_path)}",
        "--gzip",
    ]

    if args.database:
        cmd.extend(["-d", args.database])
    if args.collection:
        cmd.extend(["-c", args.collection])
    if args.mongodump_extra_args:
        cmd.extend(args.mongodump_extra_args.strip().split())

    safe_uri = mask_mongo_uri(args.mongo_uri)
    logger.info(f"Starting mongodump against: {safe_uri}")
    logger.info(f"Target archive destination: {output_path}")

    start_time = time.time()
    try:
        # Run mongodump and stream output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in iter(process.stdout.readline, ""):
            line_str = line.strip()
            if line_str:
                logger.info(f"[mongodump] {line_str}")

        process.stdout.close()
        return_code = process.wait()

        if return_code != 0:
            raise RuntimeError(f"mongodump failed with exit code {return_code}")

    except Exception as e:
        logger.error(f"Error during mongodump execution: {e}")
        if output_path.exists():
            output_path.unlink()
        raise

    duration = time.time() - start_time

    # Validate output file
    if not output_path.exists():
        raise FileNotFoundError(f"Dump output file was not created: {output_path}")

    file_size_bytes = output_path.stat().st_size
    if file_size_bytes == 0:
        output_path.unlink()
        raise ValueError("Generated dump archive is 0 bytes (empty).")

    file_size_mb = file_size_bytes / (1024 * 1024)
    logger.info(
        f"Dump completed successfully in {duration:.2f}s! Archive size: {file_size_mb:.2f} MB ({file_size_bytes} bytes)"
    )
    return output_path


def determine_s3_key(args: argparse.Namespace, archive_path: Path) -> str:
    """Generate or retrieve S3 object key."""
    if args.s3_key:
        return args.s3_key.lstrip("/")

    prefix = args.s3_prefix.strip("/")
    if prefix:
        return f"{prefix}/{archive_path.name}"
    return archive_path.name


def upload_to_s3(s3_client, local_file: Path, bucket: str, s3_key: str, storage_class: str) -> None:
    """
    Upload the dump file to S3 with multipart support and progress tracking.
    """
    file_size = local_file.stat().st_size
    logger.info(f"Starting upload to s3://{bucket}/{s3_key} (Storage Class: {storage_class})...")

    from boto3.s3.transfer import TransferConfig

    # Transfer configuration for optimal upload performance (8MB chunks, 10 concurrency)
    config = TransferConfig(
        multipart_threshold=8 * 1024 * 1024,
        max_concurrency=10,
        multipart_chunksize=8 * 1024 * 1024,
        use_threads=True,
    )

    extra_args = {
        "StorageClass": storage_class,
        "Metadata": {
            "backup_tool": "mongo-s3-backup",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "original_filename": local_file.name,
        },
    }

    progress = UploadProgressPercentage(str(local_file), file_size)

    start_time = time.time()
    s3_client.upload_file(
        Filename=str(local_file),
        Bucket=bucket,
        Key=s3_key,
        ExtraArgs=extra_args,
        Callback=progress,
        Config=config,
    )
    elapsed = time.time() - start_time
    mb_uploaded = file_size / (1024 * 1024)
    avg_speed = (mb_uploaded / elapsed) if elapsed > 0 else 0
    logger.info(
        f"S3 Upload finished in {elapsed:.2f}s! Average speed: {avg_speed:.2f} MB/s"
    )


def verify_s3_upload(s3_client, bucket: str, s3_key: str, expected_size: int) -> None:
    """Verify the uploaded object exists in S3 and matches file size."""
    logger.info(f"Verifying uploaded object in S3: s3://{bucket}/{s3_key}...")
    try:
        response = s3_client.head_object(Bucket=bucket, Key=s3_key)
        remote_size = response.get("ContentLength", 0)
        etag = response.get("ETag", "").strip('"')

        if remote_size != expected_size:
            raise ValueError(
                f"Size mismatch: local={expected_size} bytes vs S3={remote_size} bytes!"
            )

        logger.info(
            f"Verification PASSED! S3 Object verified: size={remote_size} bytes, ETag={etag}"
        )
    except Exception as e:
        logger.error(f"S3 Object verification failed: {e}")
        raise


def main() -> None:
    """Main backup and push orchestrator."""
    logger.info("=== Starting MongoDB to S3 Backup Process ===")
    args = parse_arguments()
    validate_environment(args)

    archive_path: Optional[Path] = None

    try:
        # Step 1: AWS authorization & S3 readiness
        s3_client = initialize_aws_clients(args)

        # Step 2: Execute mongodump to create compressed archive
        archive_path = execute_mongodump(args)

        # Step 3: Determine S3 destination key
        s3_key = determine_s3_key(args, archive_path)

        # Step 4: Upload to S3
        file_size = archive_path.stat().st_size
        upload_to_s3(
            s3_client=s3_client,
            local_file=archive_path,
            bucket=args.s3_bucket,
            s3_key=s3_key,
            storage_class=args.storage_class,
        )

        # Step 5: Verify upload on S3
        verify_s3_upload(
            s3_client=s3_client,
            bucket=args.s3_bucket,
            s3_key=s3_key,
            expected_size=file_size,
        )

        logger.info("==================================================")
        logger.info(f"BACKUP COMPLETE & VERIFIED: s3://{args.s3_bucket}/{s3_key}")
        logger.info("Container task successful. Exiting with status 0.")
        logger.info("==================================================")

    except Exception as exc:
        logger.error(f"FATAL: Backup failed: {exc}", exc_info=True)
        sys.exit(1)

    finally:
        # Cleanup temporary local dump file
        if archive_path and archive_path.exists():
            try:
                archive_path.unlink()
                logger.info(f"Cleaned up temporary archive file: {archive_path}")
            except Exception as cleanup_err:
                logger.warning(f"Failed to clean up temporary file: {cleanup_err}")


if __name__ == "__main__":
    main()
