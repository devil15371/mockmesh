# /Users/aman/mockmesh/tests/test_coverage.py
import boto3
import pytest
from botocore.exceptions import ClientError
import mockmesh


def test_s3_copy_object():
    """Test CopyObject: copy a file from one key to another within/across buckets"""
    with mockmesh.mockmesh():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket="src-bucket")
        s3.create_bucket(Bucket="dst-bucket")

        original_data = b"Original binary content for copy test"
        s3.put_object(Bucket="src-bucket", Key="original.txt", Body=original_data)

        # Copy across buckets
        s3.copy_object(
            CopySource="src-bucket/original.txt",
            Bucket="dst-bucket",
            Key="copied.txt"
        )

        # Verify copied object exists and matches
        result = s3.get_object(Bucket="dst-bucket", Key="copied.txt")
        assert result['Body'].read() == original_data
        print("\n[Coverage] CopyObject: Cross-bucket copy verified.")


def test_s3_delete_objects_batch():
    """Test DeleteObjects: batch delete multiple keys at once"""
    with mockmesh.mockmesh():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket="batch-bucket")
        s3.put_object(Bucket="batch-bucket", Key="a.txt", Body=b"aaa")
        s3.put_object(Bucket="batch-bucket", Key="b.txt", Body=b"bbb")
        s3.put_object(Bucket="batch-bucket", Key="c.txt", Body=b"ccc")

        # Batch delete a.txt and b.txt
        result = s3.delete_objects(
            Bucket="batch-bucket",
            Delete={'Objects': [{'Key': 'a.txt'}, {'Key': 'b.txt'}]}
        )

        assert len(result['Deleted']) == 2

        # Only c.txt should remain
        listing = s3.list_objects_v2(Bucket="batch-bucket")
        assert listing['KeyCount'] == 1
        assert listing['Contents'][0]['Key'] == 'c.txt'
        print("[Coverage] DeleteObjects: Batch deletion verified.")


def test_s3_list_buckets():
    """Test ListBuckets: list all created buckets"""
    with mockmesh.mockmesh():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket="alpha-bucket")
        s3.create_bucket(Bucket="beta-bucket")

        result = s3.list_buckets()
        bucket_names = [b['Name'] for b in result['Buckets']]
        assert "alpha-bucket" in bucket_names
        assert "beta-bucket" in bucket_names
        print(f"[Coverage] ListBuckets: Found {len(result['Buckets'])} buckets.")


def test_s3_head_object():
    """Test HeadObject: get metadata without downloading the body"""
    with mockmesh.mockmesh():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket="head-bucket")
        payload = b"Metadata test payload with known size"
        s3.put_object(Bucket="head-bucket", Key="meta.dat", Body=payload)

        head = s3.head_object(Bucket="head-bucket", Key="meta.dat")
        assert head['ContentLength'] == len(payload)
        print(f"[Coverage] HeadObject: Content-Length = {head['ContentLength']} bytes.")


def test_s3_head_bucket():
    """Test HeadBucket: verify bucket existence"""
    with mockmesh.mockmesh():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket="exists-bucket")

        # Should not throw
        s3.head_bucket(Bucket="exists-bucket")

        # Should throw for non-existent bucket
        with pytest.raises(ClientError) as exc:
            s3.head_bucket(Bucket="ghost-bucket")
        assert exc.value.response['Error']['Code'] == "NoSuchBucket"
        print("[Coverage] HeadBucket: Existence check verified.")


def test_ddb_update_item():
    """Test UpdateItem: update attributes on an existing DynamoDB item"""
    with mockmesh.mockmesh():
        db = boto3.client('dynamodb', region_name='us-east-1')
        db.create_table(
            TableName="update-table",
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'pk', 'AttributeType': 'S'}]
        )
        db.put_item(
            TableName="update-table",
            Item={'pk': {'S': 'item_1'}, 'score': {'N': '10'}, 'status': {'S': 'draft'}}
        )

        # Update score and status
        db.update_item(
            TableName="update-table",
            Key={'pk': {'S': 'item_1'}},
            UpdateExpression="SET score = :s, status = :st",
            ExpressionAttributeValues={
                ':s': {'N': '99'},
                ':st': {'S': 'published'}
            }
        )

        result = db.get_item(TableName="update-table", Key={'pk': {'S': 'item_1'}})
        assert result['Item']['score']['N'] == '99'
        assert result['Item']['status']['S'] == 'published'
        print(f"[Coverage] UpdateItem: score={result['Item']['score']['N']}, status={result['Item']['status']['S']}")


def test_ddb_update_item_with_attr_names():
    """Test UpdateItem with ExpressionAttributeNames for reserved words"""
    with mockmesh.mockmesh():
        db = boto3.client('dynamodb', region_name='us-east-1')
        db.create_table(
            TableName="reserved-table",
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}]
        )
        db.put_item(
            TableName="reserved-table",
            Item={'id': {'S': 'r1'}, 'name': {'S': 'old_name'}}
        )

        db.update_item(
            TableName="reserved-table",
            Key={'id': {'S': 'r1'}},
            UpdateExpression="SET #n = :v",
            ExpressionAttributeNames={'#n': 'name'},
            ExpressionAttributeValues={':v': {'S': 'new_name'}}
        )

        result = db.get_item(TableName="reserved-table", Key={'id': {'S': 'r1'}})
        assert result['Item']['name']['S'] == 'new_name'
        print("[Coverage] UpdateItem with ExpressionAttributeNames: verified.")


def test_ddb_batch_write_item():
    """Test BatchWriteItem: insert multiple items in one call"""
    with mockmesh.mockmesh():
        db = boto3.client('dynamodb', region_name='us-east-1')
        db.create_table(
            TableName="batch-table",
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}]
        )

        db.batch_write_item(RequestItems={
            'batch-table': [
                {'PutRequest': {'Item': {'id': {'S': 'b1'}, 'val': {'S': 'one'}}}},
                {'PutRequest': {'Item': {'id': {'S': 'b2'}, 'val': {'S': 'two'}}}},
                {'PutRequest': {'Item': {'id': {'S': 'b3'}, 'val': {'S': 'three'}}}},
            ]
        })

        scan = db.scan(TableName="batch-table")
        assert scan['Count'] == 3
        print(f"[Coverage] BatchWriteItem: Inserted {scan['Count']} items.")


def test_ddb_batch_get_item():
    """Test BatchGetItem: retrieve multiple items by key in one call"""
    with mockmesh.mockmesh():
        db = boto3.client('dynamodb', region_name='us-east-1')
        db.create_table(
            TableName="bget-table",
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}]
        )
        db.put_item(TableName="bget-table", Item={'id': {'S': 'x1'}, 'data': {'S': 'alpha'}})
        db.put_item(TableName="bget-table", Item={'id': {'S': 'x2'}, 'data': {'S': 'beta'}})
        db.put_item(TableName="bget-table", Item={'id': {'S': 'x3'}, 'data': {'S': 'gamma'}})

        result = db.batch_get_item(RequestItems={
            'bget-table': {
                'Keys': [
                    {'id': {'S': 'x1'}},
                    {'id': {'S': 'x3'}},
                ]
            }
        })

        items = result['Responses']['bget-table']
        assert len(items) == 2
        ids = [i['id']['S'] for i in items]
        assert 'x1' in ids
        assert 'x3' in ids
        print(f"[Coverage] BatchGetItem: Retrieved {len(items)} items by key.")


def test_ddb_describe_table():
    """Test DescribeTable: get table metadata"""
    with mockmesh.mockmesh():
        db = boto3.client('dynamodb', region_name='us-east-1')
        db.create_table(
            TableName="desc-table",
            KeySchema=[{'AttributeName': 'pk', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'pk', 'AttributeType': 'S'}]
        )
        db.put_item(TableName="desc-table", Item={'pk': {'S': 'd1'}})
        db.put_item(TableName="desc-table", Item={'pk': {'S': 'd2'}})

        desc = db.describe_table(TableName="desc-table")
        table = desc['Table']
        assert table['TableName'] == 'desc-table'
        assert table['TableStatus'] == 'ACTIVE'
        assert table['ItemCount'] == 2
        assert table['KeySchema'][0]['AttributeName'] == 'pk'
        print(f"[Coverage] DescribeTable: {table['TableName']} has {table['ItemCount']} items.")


def test_ddb_delete_table():
    """Test DeleteTable: remove a table and all its items"""
    with mockmesh.mockmesh():
        db = boto3.client('dynamodb', region_name='us-east-1')
        db.create_table(
            TableName="temp-table",
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}]
        )
        db.put_item(TableName="temp-table", Item={'id': {'S': 't1'}})

        # Delete the table
        result = db.delete_table(TableName="temp-table")
        assert result['TableDescription']['TableStatus'] == 'DELETING'

        # Table should no longer exist
        with pytest.raises(ClientError) as exc:
            db.describe_table(TableName="temp-table")
        assert exc.value.response['Error']['Code'] == "ResourceNotFoundException"
        print("[Coverage] DeleteTable: Table removed and verified missing.")
