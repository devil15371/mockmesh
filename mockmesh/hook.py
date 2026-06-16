# /Users/aman/mockmesh/mockmesh/hook.py
import botocore.client
from botocore.exceptions import ClientError
from .state import state_engine
from .formatter import response_formatter
from .automock import schema_compiler

class InterceptorEngine:
    def __init__(self):
        self.original_api_call = None
        self._is_patched = False

    def patch(self):
        if self._is_patched:
            return
        
        # Capture the original low-level SDK register
        self.original_api_call = botocore.client.BaseClient._make_api_call

        def _custom_hook(client_instance, operation_name, kwargs):
            service_name = client_instance.meta.service_model.service_name
            
            # Check if target is an AWS S3 operation
            if service_name == 's3':
                try:
                    return self.route_s3(operation_name, kwargs)
                except ClientError as ce:
                    # Re-raise expected client validations cleanly without error logging
                    raise ce
                except NotImplementedError:
                    # Fall through to auto-mock for unmapped S3 operations
                    pass
                except Exception as e:
                    # Fallback to prevent silent app crashes during debugging
                    print(f"[MockMesh System Alert] Unexpected simulation failure on {operation_name}: {e}")
                    raise e
            
            elif service_name == 'dynamodb':
                try:
                    return self.route_dynamodb(operation_name, kwargs)
                except ClientError as ce:
                    raise ce
                except NotImplementedError:
                    # Fall through to auto-mock for unmapped DynamoDB operations
                    pass
                except Exception as e:
                    print(f"[MockMesh System Alert] Unexpected simulation failure on {operation_name}: {e}")
                    raise e
            
            # Universal Auto-Mock Fallback: use botocore's schema to generate responses
            if schema_compiler.can_handle(service_name, operation_name):
                return schema_compiler.generate_response(service_name, operation_name, kwargs)

            # Last resort: forward to real AWS (will fail without network)
            return self.original_api_call(client_instance, operation_name, kwargs)

        # Overwrite the base execution function in Python memory
        botocore.client.BaseClient._make_api_call = _custom_hook
        self._is_patched = True
        print("[MockMesh] In-Process Interception Enabled.")

    def unpatch(self):
        if not self._is_patched:
            return
        # Restore original function register
        botocore.client.BaseClient._make_api_call = self.original_api_call
        self._is_patched = False
        print("[MockMesh] In-Process Interception Disabled.")

    def route_s3(self, operation, kwargs):
        """Routes python arguments directly into the in-memory state engine"""
        if operation == 'CreateBucket':
            bucket = kwargs.get('Bucket')
            state_engine.create_bucket(bucket)
            return response_formatter.format_create_bucket(bucket)
            
        elif operation == 'PutObject':
            bucket = kwargs.get('Bucket')
            key = kwargs.get('Key')
            body = kwargs.get('Body')
            
            # Read streaming bytes safely from the file wrapper
            if hasattr(body, 'read'):
                data = body.read()
            else:
                data = body if isinstance(body, bytes) else str(body).encode('utf-8')
                
            state_engine.put_object(bucket, key, data)
            return response_formatter.format_put_object(key)

        elif operation == 'GetObject':
            bucket = kwargs.get('Bucket')
            key = kwargs.get('Key')
            
            data = state_engine.get_object(bucket, key)
            return response_formatter.format_get_object(key, data)

        elif operation == 'ListObjectsV2':
            bucket = kwargs.get('Bucket')
            prefix = kwargs.get('Prefix', '')
            obj_list = state_engine.list_s3_objects(bucket, prefix)
            return response_formatter.format_list_objects_v2(bucket, prefix, obj_list)

        elif operation == 'DeleteObject':
            bucket = kwargs.get('Bucket')
            key = kwargs.get('Key')
            state_engine.delete_object(bucket, key)
            return response_formatter.format_delete_object()

        elif operation == 'CopyObject':
            copy_source = kwargs.get('CopySource', '')
            # CopySource can be a string 'bucket/key' or dict {'Bucket': ..., 'Key': ...}
            if isinstance(copy_source, dict):
                src_bucket = copy_source['Bucket']
                src_key = copy_source['Key']
            else:
                parts = copy_source.lstrip('/').split('/', 1)
                src_bucket = parts[0]
                src_key = parts[1] if len(parts) > 1 else ''
            dst_bucket = kwargs.get('Bucket')
            dst_key = kwargs.get('Key')
            state_engine.copy_object(src_bucket, src_key, dst_bucket, dst_key)
            return response_formatter.format_copy_object(dst_key)

        elif operation == 'DeleteObjects':
            bucket = kwargs.get('Bucket')
            delete_spec = kwargs.get('Delete', {})
            objects_to_delete = delete_spec.get('Objects', [])
            keys = [obj['Key'] for obj in objects_to_delete]
            deleted, errors = state_engine.delete_objects_batch(bucket, keys)
            return response_formatter.format_delete_objects(deleted, errors)

        elif operation == 'ListBuckets':
            buckets = state_engine.list_buckets()
            return response_formatter.format_list_buckets(buckets)

        elif operation == 'HeadBucket':
            bucket = kwargs.get('Bucket')
            cursor = state_engine.conn.cursor()
            cursor.execute("SELECT 1 FROM buckets WHERE name = ?", (bucket,))
            if not cursor.fetchone():
                raise ClientError(
                    {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist."}},
                    "HeadBucket"
                )
            return response_formatter.format_head_bucket()

        elif operation == 'HeadObject':
            bucket = kwargs.get('Bucket')
            key = kwargs.get('Key')
            metadata = state_engine.head_object(bucket, key)
            return response_formatter.format_head_object(metadata)

        raise NotImplementedError(f"MockMesh hasn't mapped S3 method: {operation}")

    def route_dynamodb(self, operation, kwargs):
        table_name = kwargs.get('TableName')
        
        if operation == 'CreateTable':
            # Extract the partition key attribute name from KeySchema
            hash_key = kwargs.get('KeySchema')[0]['AttributeName']
            state_engine.create_ddb_table(table_name, hash_key)
            return response_formatter.format_create_table(table_name)
            
        elif operation == 'PutItem':
            item = kwargs.get('Item')
            state_engine.put_ddb_item(table_name, item)
            return response_formatter.format_put_item()
            
        elif operation == 'GetItem':
            key = kwargs.get('Key')
            item_data = state_engine.get_ddb_item(table_name, key)
            return response_formatter.format_get_item(item_data)

        elif operation == 'Query':
            val_attrs = kwargs.get('ExpressionAttributeValues', {})
            items = state_engine.query_ddb_items(table_name, val_attrs)
            return response_formatter.format_ddb_query(items)

        elif operation == 'Scan':
            items = state_engine.scan_ddb_items(table_name)
            return response_formatter.format_ddb_scan(items)

        elif operation == 'DeleteItem':
            key = kwargs.get('Key')
            state_engine.delete_ddb_item(table_name, key)
            return response_formatter.format_delete_ddb_item()

        elif operation == 'ListTables':
            tables = state_engine.list_ddb_tables()
            return response_formatter.format_list_ddb_tables(tables)

        elif operation == 'UpdateItem':
            key = kwargs.get('Key')
            update_expr = kwargs.get('UpdateExpression', '')
            expr_attr_values = kwargs.get('ExpressionAttributeValues', {})
            expr_attr_names = kwargs.get('ExpressionAttributeNames', None)
            updated = state_engine.update_ddb_item(table_name, key, update_expr, expr_attr_values, expr_attr_names)
            return response_formatter.format_update_item(updated)

        elif operation == 'BatchWriteItem':
            request_items = kwargs.get('RequestItems', {})
            state_engine.batch_write_ddb_items(request_items)
            return response_formatter.format_batch_write()

        elif operation == 'BatchGetItem':
            request_items = kwargs.get('RequestItems', {})
            results = state_engine.batch_get_ddb_items(request_items)
            return response_formatter.format_batch_get(results)

        elif operation == 'DescribeTable':
            desc = state_engine.describe_ddb_table(table_name)
            return response_formatter.format_describe_table(desc)

        elif operation == 'DeleteTable':
            state_engine.delete_ddb_table(table_name)
            return response_formatter.format_delete_table(table_name)
            
        raise NotImplementedError(f"MockMesh hasn't mapped DynamoDB method: {operation}")

interceptor_engine = InterceptorEngine()
