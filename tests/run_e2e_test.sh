#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "Running End-to-End Mongo to S3 Backup Test"
echo "=========================================="

NETWORK_NAME="mongo-test-net-$$"
MONGO_CONTAINER="test-mongo-$$"
MOCK_S3_CONTAINER="test-mocks3-$$"

cleanup() {
    echo "Cleaning up test containers..."
    docker rm -f "${MONGO_CONTAINER}" 2>/dev/null || true
    docker rm -f "${MOCK_S3_CONTAINER}" 2>/dev/null || true
    docker network rm "${NETWORK_NAME}" 2>/dev/null || true
}
trap cleanup EXIT

echo "1. Creating isolated test Docker network: ${NETWORK_NAME}"
docker network create "${NETWORK_NAME}"

echo "2. Starting MongoDB container: ${MONGO_CONTAINER}"
docker run -d --name "${MONGO_CONTAINER}" --network "${NETWORK_NAME}" mongo:7

echo "Waiting for MongoDB to become ready..."
for i in {1..30}; do
    if docker exec "${MONGO_CONTAINER}" mongosh --eval "db.adminCommand('ping')" >/dev/null 2>&1; then
        echo "MongoDB is ready!"
        break
    fi
    sleep 1
done

echo "3. Seeding test data into MongoDB..."
docker exec "${MONGO_CONTAINER}" mongosh --eval "
    use test_db;
    db.users.insertMany([
        { name: 'Alice', email: 'alice@example.com', role: 'admin' },
        { name: 'Bob', email: 'bob@example.com', role: 'engineer' },
        { name: 'Charlie', email: 'charlie@example.com', role: 'designer' }
    ]);
    print('Inserted count: ' + db.users.countDocuments());
"

echo "4. Starting Mock S3 service inside network..."
docker run -d --name "${MOCK_S3_CONTAINER}" \
    --network "${NETWORK_NAME}" \
    -v "$(pwd)/tests/mock_s3.py:/app/mock_s3.py:ro" \
    python:3.14-alpine python /app/mock_s3.py 9005

sleep 2

echo "5. Running backup container (anuragbhatt1805/mongos3:latest)..."
docker run --rm \
    --network "${NETWORK_NAME}" \
    -e MONGO_URI="mongodb://${MONGO_CONTAINER}:27017" \
    -e S3_BUCKET="test-backup-bucket" \
    -e S3_PREFIX="backups/daily" \
    -e S3_ENDPOINT_URL="http://${MOCK_S3_CONTAINER}:9005" \
    -e AWS_ACCESS_KEY_ID="mock_access_key" \
    -e AWS_SECRET_ACCESS_KEY="mock_secret_key" \
    -e AWS_REGION="us-east-1" \
    anuragbhatt1805/mongos3:latest

echo ""
echo "=========================================="
echo "✅ End-to-End Test PASSED Successfully!"
echo "=========================================="
