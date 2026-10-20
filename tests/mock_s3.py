"""
Minimal Mock S3 Server for End-to-End Testing
==============================================
Handles basic S3 operations used by boto3:
- HEAD /bucket
- PUT /bucket/key (upload)
- HEAD /bucket/key (verify content-length and etag)
"""

import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
import threading

objects = {}


class MockS3Handler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        parts = self.path.split("?")[0].strip("/").split("/", 1)
        if len(parts) == 1:
            # Bucket check (head_bucket)
            self.send_response(200)
            self.send_header("Content-Type", "application/xml")
            self.end_headers()
            return
        elif len(parts) == 2:
            bucket, key = parts
            if key in objects:
                data = objects[key]
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("ETag", f'"{hashlib.md5(data).hexdigest()}"')
                self.end_headers()
                return
        self.send_response(404)
        self.end_headers()

    def do_PUT(self):
        parts = self.path.split("?")[0].strip("/").split("/", 1)
        if len(parts) == 2:
            bucket, key = parts
            content_length = int(self.headers.get("Content-Length", 0))
            payload = self.rfile.read(content_length)
            objects[key] = payload
            md5_hash = hashlib.md5(payload).hexdigest()
            self.send_response(200)
            self.send_header("ETag", f'"{md5_hash}"')
            self.end_headers()
            return
        self.send_response(400)
        self.end_headers()

    def log_message(self, format, *args):
        sys.stderr.write(f"[MockS3] {args[0]} {args[1]} -> {args[2]}\n")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9005
    server = HTTPServer(("0.0.0.0", port), MockS3Handler)
    print(f"Mock S3 server running on port {port}...")
    server.serve_forever()
