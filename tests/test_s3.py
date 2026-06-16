# /Users/aman/mockmesh/tests/test_s3.py
import boto3
import pytest
from botocore.exceptions import ClientError
import mockmesh

def test_mockmesh_s3_lifecycle():
    # Execute the workflow inside our custom context manager
    with mockmesh.mockmesh():
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = "test-system-bucket"
        file_key = "logs/manifest.txt"
        payload = b"Hello World from MockMesh Offline Silicon System"

        # 1. Test Stateful Bucket Creation
        s3.create_bucket(Bucket=bucket_name)

        # 2. Test Duplicate Error Verification
        with pytest.raises(ClientError) as exc:
            s3.create_bucket(Bucket=bucket_name)
        assert exc.value.response['Error']['Code'] == "BucketAlreadyExists"

        # 3. Test Object Upload
        put_res = s3.put_object(Bucket=bucket_name, Key=file_key, Body=payload)
        assert 'ETag' in put_res

        # 4. Test Object Download and Data Validation
        get_res = s3.get_object(Bucket=bucket_name, Key=file_key)
        assert get_res['ContentLength'] == len(payload)
        
        fetched_content = get_res['Body'].read()
        assert fetched_content == payload
        print(f"\n[Verification Match] Fetched data matches payload flawlessly: {fetched_content}")

def test_mockmesh_cache_cleanup():
    import mockmesh
    import boto3
    import os
    from mockmesh.state import state_engine

    bucket = "cleanup-bucket"
    key = "temp-asset.dat"

    with mockmesh.mockmesh():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket=bucket)
        s3.put_object(Bucket=bucket, Key=key, Body=b"Temporary Data Stream")

    # Verify the physical file is present on the laptop disk right now
    safe_file_name = key.replace("/", "___")
    expected_file_path = state_engine.storage_root / bucket / safe_file_name
    assert expected_file_path.exists()

    # Trigger the global reset tool
    mockmesh.clean()

    # Verify the tracking file is completely deleted from the laptop hard drive
    assert not expected_file_path.exists()
    print("\n[Cleanup Verification Match] Cache folder wiped cleanly from filesystem.")
