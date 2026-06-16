# /Users/aman/mockmesh/mockmesh/formatter.py
import hashlib
from botocore.response import StreamingBody
from io import BytesIO

class ResponseFormatter:
    def _base_metadata(self):
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'HTTPHeaders': {
                    'x-amz-request-id': 'MOCKMESH123456789',
                    'content-type': 'application/xml',
                    'server': 'AmazonS3'
                }
            }
        }

    def format_create_bucket(self, bucket_name):
        res = self._base_metadata()
        res['Location'] = f'/{bucket_name}'
        return res

    def format_put_object(self, key):
        res = self._base_metadata()
        # Calculate a deterministic local ETag checksum wrapper
        checksum = hashlib.md5(key.encode('utf-8')).hexdigest()
        res['ETag'] = f'"{checksum}"'
        return res

    def format_get_object(self, key, binary_data):
        res = self._base_metadata()
        # Re-encode raw bytes into a streaming wrapper that boto3's .read() layer expects
        raw_stream = BytesIO(binary_data)
        res['Body'] = StreamingBody(raw_stream, len(binary_data))
        res['ContentLength'] = len(binary_data)
        res['ETag'] = f'"{hashlib.md5(binary_data).hexdigest()}"'
        return res

    def format_create_table(self, table_name):
        res = self._base_metadata()
        res['TableDescription'] = {
            'TableName': table_name,
            'TableStatus': 'ACTIVE',
            'ItemCount': 0
        }
        return res

    def format_put_item(self):
        return self._base_metadata()

    def format_get_item(self, item_data):
        res = self._base_metadata()
        if item_data:
            res['Item'] = item_data
        return res

    def format_list_objects_v2(self, bucket, prefix, object_list):
        res = self._base_metadata()
        res.update({
            'Name': bucket,
            'Prefix': prefix,
            'KeyCount': len(object_list),
            'MaxKeys': 1000,
            'IsTruncated': False
        })
        if object_list:
            res['Contents'] = object_list
        return res

    def format_ddb_query(self, items_list):
        res = self._base_metadata()
        res.update({
            'Items': items_list,
            'Count': len(items_list),
            'ScannedCount': len(items_list)
        })
        return res

    def format_delete_object(self):
        return self._base_metadata()

    def format_ddb_scan(self, items_list):
        res = self._base_metadata()
        res.update({
            'Items': items_list,
            'Count': len(items_list),
            'ScannedCount': len(items_list)
        })
        return res

    def format_delete_ddb_item(self):
        return self._base_metadata()

    def format_list_ddb_tables(self, tables_list):
        res = self._base_metadata()
        res.update({
            'TableNames': tables_list
        })
        return res

    def format_copy_object(self, key):
        import hashlib
        res = self._base_metadata()
        res['CopyObjectResult'] = {
            'ETag': f'"{hashlib.md5(key.encode()).hexdigest()}"',
            'LastModified': '2026-01-01T00:00:00.000Z'
        }
        return res

    def format_delete_objects(self, deleted_keys, error_keys):
        res = self._base_metadata()
        res['Deleted'] = [{'Key': k} for k in deleted_keys]
        if error_keys:
            res['Errors'] = [{'Key': k, 'Code': 'InternalError', 'Message': 'Failed to delete'} for k in error_keys]
        return res

    def format_list_buckets(self, buckets_list):
        res = self._base_metadata()
        res['Buckets'] = buckets_list
        res['Owner'] = {'DisplayName': 'mockmesh-user', 'ID': 'mockmesh-owner-id'}
        return res

    def format_head_object(self, metadata):
        res = self._base_metadata()
        res['ContentLength'] = metadata['ContentLength']
        res['LastModified'] = metadata['LastModified']
        res['ContentType'] = 'application/octet-stream'
        return res

    def format_head_bucket(self):
        return self._base_metadata()

    def format_update_item(self, updated_item):
        res = self._base_metadata()
        res['Attributes'] = updated_item
        return res

    def format_batch_write(self):
        res = self._base_metadata()
        res['UnprocessedItems'] = {}
        return res

    def format_batch_get(self, results):
        res = self._base_metadata()
        res['Responses'] = results
        res['UnprocessedKeys'] = {}
        return res

    def format_describe_table(self, table_desc):
        res = self._base_metadata()
        res['Table'] = table_desc
        return res

    def format_delete_table(self, table_name):
        res = self._base_metadata()
        res['TableDescription'] = {
            'TableName': table_name,
            'TableStatus': 'DELETING'
        }
        return res

response_formatter = ResponseFormatter()
