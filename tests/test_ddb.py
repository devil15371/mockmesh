# /Users/aman/mockmesh/tests/test_ddb.py
import boto3
import pytest
from botocore.exceptions import ClientError
import mockmesh

def test_mockmesh_dynamodb_lifecycle():
    with mockmesh.mockmesh():
        db_client = boto3.client('dynamodb', region_name='us-east-1')
        table = "users-table"
        
        # 1. Create a Fake NoSQL Table in RAM
        db_client.create_table(
            TableName=table,
            KeySchema=[{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'user_id', 'AttributeType': 'S'}]
        )
        
        # 2. Insert a Mock Document
        db_client.put_item(
            TableName=table,
            Item={
                'user_id': {'S': 'aman_kumar_2026'},
                'role': {'S': 'Systems_Architect'},
                'status': {'S': 'Active'}
            }
        )
        
        # 3. Retrieve and Validate Document Properties
        response = db_client.get_item(TableName=table, Key={'user_id': {'S': 'aman_kumar_2026'}})
        
        assert 'Item' in response
        assert response['Item']['role']['S'] == 'Systems_Architect'
        print(f"\n[NoSQL Verification Match] Fetched document user role: {response['Item']['role']['S']}")


def test_mockmesh_advanced_query_loop():
    import mockmesh
    import boto3

    with mockmesh.mockmesh():
        s3 = boto3.client('s3', region_name='us-east-1')
        db = boto3.client('dynamodb', region_name='us-east-1')

        # 1. Test S3 Prefix Listing
        s3.create_bucket(Bucket="media-bucket")
        s3.put_object(Bucket="media-bucket", Key="uploads/vid1.mp4", Body=b"...")
        s3.put_object(Bucket="media-bucket", Key="raw/data.txt", Body=b"...")

        listing = s3.list_objects_v2(Bucket="media-bucket", Prefix="uploads/")
        assert listing['KeyCount'] == 1
        assert listing['Contents'][0]['Key'] == "uploads/vid1.mp4"
        print("\n[Advanced S3 Match] Prefix filter successfully isolated upload vectors.")

        # 2. Test DynamoDB Expression Filtering
        db.create_table(
            TableName="device-logs",
            KeySchema=[{'AttributeName': 'device_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'device_id', 'AttributeType': 'S'}]
        )
        db.put_item(TableName="device-logs", Item={'device_id': {'S': 'dev_alpha'}, 'val': {'N': '42'}})

        query_res = db.query(
            TableName="device-logs",
            KeyConditionExpression="device_id = :d",
            ExpressionAttributeValues={':d': {'S': 'dev_alpha'}}
        )
        assert len(query_res['Items']) == 1
        print(f"[Advanced NoSQL Match] Query expression matched target record value: {query_res['Items'][0]['val']['N']}")
