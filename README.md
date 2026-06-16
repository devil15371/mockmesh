# ⚡ MockMesh

An in-process, schema-driven, zero-container AWS auto-mocking library for Python developers. **Run integration tests across 420+ AWS services in milliseconds with 0MB Docker overhead.**

## 🚀 Why MockMesh?

* **Sub-Second Feedback Loop:** Run full AWS lifecycles in milliseconds instead of waiting for heavy containers to boot.
* **426 AWS Services Out-of-the-Box:** Powered by a recursive compiler engine that reads `botocore` JSON schemas natively to auto-generate contextually realistic responses (ARNs, UUIDs, ISO timestamps) for unmapped services.
* **Three-Tier Routing:** High-fidelity stateful handlers (S3/DynamoDB) take priority ➔ Auto-Mock compiler covers the rest ➔ Real AWS passthrough as a last resort.
* **Hybrid Caching:** Stores metadata in lightning-fast in-memory SQLite tables, while streaming massive binary payloads directly to a local file cache to prevent RAM saturation.
* **Standalone Server:** Run `mockmesh start` to launch a language-agnostic HTTP server on port 4566 with a premium dark-mode Developer Console.

## 🛠️ Quick Start

```bash
pip install mockmesh
```

### Python In-Process (Sub-Second Offline Tests)

```python
import boto3
import mockmesh

# Use as a global switch or a scoped context manager
with mockmesh.mockmesh():
    # 1. High-Fidelity Stateful S3 Handler (Hybrid Local Cache)
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket="media-pipeline")
    s3.put_object(Bucket="media-pipeline", Key="vid.mp4", Body=b"binary_stream")

    # 2. Schema-Driven Auto-Mock (SQS, Lambda, Secrets Manager, etc.)
    sqs = boto3.client('sqs', region_name='us-east-1')
    response = sqs.create_queue(QueueName="orders-queue")
    print(response) # Auto-generates a perfectly structured QueueUrl and Metadata!
```

### Standalone Server (For Node.js, Go, or CLI Scripts)

```bash
# Start MockMesh on port 4566
mockmesh start --port 4566

# Connect from any AWS SDK or CLI
aws s3api create-bucket --bucket dev-bucket --endpoint-url http://localhost:4566
```

Open `http://localhost:4566/dashboard` to inspect your local state visually.

## 🏗️ Architecture

```
Developer's boto3 call
        │
        ▼
[1] Hand-coded handlers (S3, DynamoDB) → Stateful, high-fidelity, 21 operations
        │ (if unmapped)
        ▼
[2] Auto-Mock Schema Compiler → Reads botocore JSON, covers 426 services
        │ (if service not found)
        ▼
[3] Real AWS passthrough → Last resort
```

## 📊 Supported Operations

### S3 (Stateful — Full Lifecycle)
`CreateBucket` · `PutObject` · `GetObject` · `DeleteObject` · `ListObjectsV2` · `CopyObject` · `DeleteObjects` · `ListBuckets` · `HeadObject` · `HeadBucket`

### DynamoDB (Stateful — Full Lifecycle)
`CreateTable` · `PutItem` · `GetItem` · `DeleteItem` · `Query` · `Scan` · `ListTables` · `UpdateItem` · `BatchWriteItem` · `BatchGetItem` · `DescribeTable` · `DeleteTable`

### Everything Else (Auto-Mock Compiler)
SQS · SNS · Lambda · STS · Secrets Manager · KMS · IAM · CloudWatch · EventBridge · Step Functions · **and 416 more** — all auto-generated from botocore's native JSON schemas at runtime.

## 🧹 Cache Maintenance

```python
import mockmesh
mockmesh.clean()
```

## 🧪 Testing

```bash
PYTHONPATH=. pytest tests/ -s -v
# 25 passed in 7.70s
```

## 📄 License

Distributed under the MIT License. Built entirely for free by Aman Kumar.
