# /Users/aman/mockmesh/tests/test_server.py
import boto3
import urllib.request
import json
import time
import mockmesh

def test_standalone_network_server():
    # Start standalone server on a custom test port
    test_port = 5005
    mockmesh.start_server(port=test_port, block=False)
    time.sleep(0.5) # Let the background thread boot up

    endpoint = f"http://localhost:{test_port}"

    try:
        # 1. Verify S3 stand-alone emulation
        s3 = boto3.client(
            's3',
            region_name='us-east-1',
            endpoint_url=endpoint,
            aws_access_key_id='mock_key',
            aws_secret_access_key='mock_secret'
        )
        bucket = "standalone-bucket"
        key = "docs/guide.md"
        payload = b"Standalone S3 Payload Content"

        # Create Bucket
        s3.create_bucket(Bucket=bucket)

        # Put Object
        s3.put_object(Bucket=bucket, Key=key, Body=payload)

        # Get Object
        get_res = s3.get_object(Bucket=bucket, Key=key)
        assert get_res['Body'].read() == payload

        # List Objects
        listing = s3.list_objects_v2(Bucket=bucket, Prefix="docs/")
        assert listing['KeyCount'] == 1
        assert listing['Contents'][0]['Key'] == key

        # Delete Object
        s3.delete_object(Bucket=bucket, Key=key)

        # Verify deletion via list
        listing_after = s3.list_objects_v2(Bucket=bucket)
        assert 'Contents' not in listing_after or len(listing_after['Contents']) == 0

        # 2. Verify DynamoDB stand-alone emulation
        db = boto3.client(
            'dynamodb',
            region_name='us-east-1',
            endpoint_url=endpoint,
            aws_access_key_id='mock_key',
            aws_secret_access_key='mock_secret'
        )
        table = "standalone-table"

        # Create Table
        db.create_table(
            TableName=table,
            KeySchema=[{'AttributeName': 'item_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'item_id', 'AttributeType': 'S'}]
        )

        # Put Item
        db.put_item(
            TableName=table,
            Item={'item_id': {'S': 'id_999'}, 'desc': {'S': 'MockMesh Server Test'}}
        )

        # Get Item
        get_db = db.get_item(TableName=table, Key={'item_id': {'S': 'id_999'}})
        assert 'Item' in get_db
        assert get_db['Item']['desc']['S'] == 'MockMesh Server Test'

        # Scan
        scan_db = db.scan(TableName=table)
        assert scan_db['Count'] == 1
        assert scan_db['Items'][0]['item_id']['S'] == 'id_999'

        # Delete Item
        db.delete_item(TableName=table, Key={'item_id': {'S': 'id_999'}})
        scan_after = db.scan(TableName=table)
        assert scan_after['Count'] == 0

        # 3. Verify Admin Console API Endpoint
        req = urllib.request.Request(f"{endpoint}/_api/state")
        with urllib.request.urlopen(req) as response:
            assert response.status == 200
            data = json.loads(response.read().decode('utf-8'))
            assert "s3" in data
            assert "dynamodb" in data
            # The database should reflect the created bucket and table
            assert any(b['name'] == bucket for b in data['s3']['buckets'])
            assert any(t['table_name'] == table for t in data['dynamodb']['tables'])

        # 4. Verify Wipe/Clean Admin API
        req_clean = urllib.request.Request(f"{endpoint}/_api/clean", method='POST')
        with urllib.request.urlopen(req_clean) as response:
            assert response.status == 200
            clean_res = json.loads(response.read().decode('utf-8'))
            assert clean_res['status'] == 'success'

        # Confirm state is wiped clean
        req_after = urllib.request.Request(f"{endpoint}/_api/state")
        with urllib.request.urlopen(req_after) as response:
            data_after = json.loads(response.read().decode('utf-8'))
            assert len(data_after['s3']['buckets']) == 0
            assert len(data_after['dynamodb']['tables']) == 0

    finally:
        # Tear down standalone server
        mockmesh.stop_server()
