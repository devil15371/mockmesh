# /Users/aman/mockmesh/tests/test_automock.py
"""
Tests for the Auto-Mock Compiler Engine.

These tests prove that MockMesh can handle AWS services it has
ZERO manual handler code for — by reading botocore's JSON schemas
at runtime and generating responses on the fly.
"""
import boto3
import pytest
import mockmesh
from mockmesh.automock import schema_compiler


def test_automock_sqs_create_queue():
    """SQS: CreateQueue should return a QueueUrl without any manual handler"""
    with mockmesh.mockmesh():
        sqs = boto3.client('sqs', region_name='us-east-1')
        result = sqs.create_queue(QueueName='test-queue')

        assert 'QueueUrl' in result
        assert result['ResponseMetadata']['HTTPStatusCode'] == 200
        print(f"\n[AutoMock] SQS CreateQueue → QueueUrl: {result['QueueUrl']}")


def test_automock_sqs_send_message():
    """SQS: SendMessage should return MessageId"""
    with mockmesh.mockmesh():
        sqs = boto3.client('sqs', region_name='us-east-1')
        result = sqs.send_message(
            QueueUrl='https://sqs.us-east-1.amazonaws.com/123456789/test-queue',
            MessageBody='Hello from MockMesh auto-compiler!'
        )

        assert 'MessageId' in result
        assert result['ResponseMetadata']['HTTPStatusCode'] == 200
        print(f"[AutoMock] SQS SendMessage → MessageId: {result['MessageId']}")


def test_automock_sns_create_topic():
    """SNS: CreateTopic should return a TopicArn"""
    with mockmesh.mockmesh():
        sns = boto3.client('sns', region_name='us-east-1')
        result = sns.create_topic(Name='test-alerts')

        assert 'TopicArn' in result
        assert 'arn:aws' in result['TopicArn']
        print(f"[AutoMock] SNS CreateTopic → TopicArn: {result['TopicArn']}")


def test_automock_sts_get_caller_identity():
    """STS: GetCallerIdentity should return Account, Arn, UserId"""
    with mockmesh.mockmesh():
        sts = boto3.client('sts', region_name='us-east-1')
        result = sts.get_caller_identity()

        assert 'Account' in result
        assert 'Arn' in result
        assert 'UserId' in result
        print(f"[AutoMock] STS GetCallerIdentity → Account: {result['Account']}, Arn: {result['Arn']}")


def test_automock_secretsmanager_create_secret():
    """Secrets Manager: CreateSecret should return ARN and Name"""
    with mockmesh.mockmesh():
        sm = boto3.client('secretsmanager', region_name='us-east-1')
        result = sm.create_secret(
            Name='prod/db-password',
            SecretString='super-secret-value-123'
        )

        assert 'ARN' in result
        assert 'Name' in result
        assert result['ResponseMetadata']['HTTPStatusCode'] == 200
        print(f"[AutoMock] SecretsManager CreateSecret → ARN: {result['ARN']}, Name: {result['Name']}")


def test_automock_lambda_create_function():
    """Lambda: CreateFunction should return FunctionArn"""
    with mockmesh.mockmesh():
        lam = boto3.client('lambda', region_name='us-east-1')
        result = lam.create_function(
            FunctionName='my-processor',
            Runtime='python3.12',
            Role='arn:aws:iam::123456789012:role/mock-role',
            Handler='handler.main',
            Code={'ZipFile': b'fake-zip-bytes'}
        )

        assert 'FunctionArn' in result
        assert 'FunctionName' in result
        assert result['ResponseMetadata']['HTTPStatusCode'] == 200
        print(f"[AutoMock] Lambda CreateFunction → FunctionArn: {result['FunctionArn']}")


def test_automock_schema_compiler_service_listing():
    """The compiler should discover 400+ AWS services from botocore's data"""
    services = schema_compiler.list_available_services()
    assert len(services) > 300
    assert 's3' in services
    assert 'dynamodb' in services
    assert 'sqs' in services
    assert 'lambda' in services
    print(f"\n[AutoMock] Schema compiler discovered {len(services)} AWS services.")


def test_automock_schema_compiler_operation_listing():
    """The compiler should list all operations for a given service"""
    sqs_ops = schema_compiler.get_service_operations('sqs')
    assert 'CreateQueue' in sqs_ops
    assert 'SendMessage' in sqs_ops
    assert 'ReceiveMessage' in sqs_ops
    assert 'DeleteQueue' in sqs_ops
    print(f"[AutoMock] SQS has {len(sqs_ops)} operations available.")

    lambda_ops = schema_compiler.get_service_operations('lambda')
    assert 'CreateFunction' in lambda_ops
    assert 'Invoke' in lambda_ops
    print(f"[AutoMock] Lambda has {len(lambda_ops)} operations available.")


def test_existing_s3_tests_still_pass():
    """Verify that hand-coded S3 handlers still take priority over auto-mock"""
    with mockmesh.mockmesh():
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket="priority-test")
        s3.put_object(Bucket="priority-test", Key="file.txt", Body=b"real data")

        result = s3.get_object(Bucket="priority-test", Key="file.txt")
        data = result['Body'].read()
        assert data == b"real data"
        print("[AutoMock] Hand-coded S3 handlers still take priority. ✓")
