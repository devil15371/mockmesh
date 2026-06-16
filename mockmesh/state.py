# /Users/aman/mockmesh/mockmesh/state.py
import sqlite3
import os
from pathlib import Path
from botocore.exceptions import ClientError

class StateEngine:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        # Define a local hidden storage directory on the user's machine
        self.storage_root = Path(os.path.expanduser("~/.mockmesh/s3"))
        self.storage_root.mkdir(parents=True, exist_ok=True)
        self._bootstrap()

    def _bootstrap(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS buckets (
                name TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # We store the physical local file_path instead of a heavy database BLOB
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS objects (
                bucket TEXT,
                key TEXT,
                local_path TEXT,
                size INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (bucket, key),
                FOREIGN KEY(bucket) REFERENCES buckets(name)
            )
        """)
        
        # --- NEW: DynamoDB NoSQL Schemas ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ddb_tables (
                table_name TEXT PRIMARY KEY,
                hash_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ddb_items (
                table_name TEXT,
                partition_key_val TEXT,
                attributes_json TEXT,
                PRIMARY KEY (table_name, partition_key_val),
                FOREIGN KEY(table_name) REFERENCES ddb_tables(table_name)
            )
        """)
        self.conn.commit()

    def create_bucket(self, name):
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO buckets (name) VALUES (?)", (name,))
            self.conn.commit()
            # Physically partition a local storage bucket directory
            (self.storage_root / name).mkdir(parents=True, exist_ok=True)
        except sqlite3.IntegrityError:
            raise ClientError(
                {"Error": {"Code": "BucketAlreadyExists", "Message": f"Bucket {name} already exists"}},
                "CreateBucket"
            )

    def put_object(self, bucket, key, data):
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM buckets WHERE name = ?", (bucket,))
        if not cursor.fetchone():
            raise ClientError(
                {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist."}},
                "PutObject"
            )
        
        # Determine a safe, flat file structure location on disk
        # Replacing slashes avoids directory traversal configuration breaks
        safe_file_name = key.replace("/", "___")
        target_file_path = self.storage_root / bucket / safe_file_name
        
        # Stream the binary data out of RAM onto the local laptop disk
        with open(target_file_path, "wb") as f:
            f.write(data)

        cursor.execute("""
            INSERT OR REPLACE INTO objects (bucket, key, local_path, size) 
            VALUES (?, ?, ?, ?)
        """, (bucket, key, str(target_file_path), len(data)))
        self.conn.commit()

    def get_object(self, bucket, key):
        cursor = self.conn.cursor()
        cursor.execute("SELECT local_path FROM objects WHERE bucket = ? AND key = ?", (bucket, key))
        row = cursor.fetchone()
        if not row:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
                "GetObject"
            )
        
        # Read the binary bytes back from the physical file path
        with open(row[0], "rb") as f:
            return f.read()

    # --- Advanced S3: ListObjectsV2 ---
    def list_s3_objects(self, bucket, prefix=""):
        cursor = self.conn.cursor()
        # Verify bucket exists
        cursor.execute("SELECT 1 FROM buckets WHERE name = ?", (bucket,))
        if not cursor.fetchone():
            raise ClientError(
                {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist."}},
                "ListObjectsV2"
            )
        
        # Use SQL 'LIKE' pattern matching to handle prefixes instantly in RAM
        cursor.execute("""
            SELECT key, size, updated_at FROM objects 
            WHERE bucket = ? AND key LIKE ?
        """, (bucket, f"{prefix}%"))
        rows = cursor.fetchall()
        
        return [
            {'Key': row[0], 'Size': row[1], 'LastModified': row[2], 'StorageClass': 'STANDARD'}
            for row in rows
        ]

    # --- New DynamoDB State Core Methods ---
    def create_ddb_table(self, table_name, hash_key):
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO ddb_tables (table_name, hash_key) VALUES (?, ?)", (table_name, hash_key))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ClientError(
                {"Error": {"Code": "ResourceInUseException", "Message": f"Table {table_name} already exists"}},
                "CreateTable"
            )

    def put_ddb_item(self, table_name, item_dict):
        cursor = self.conn.cursor()
        # Look up the defined partition/hash key for this table
        cursor.execute("SELECT hash_key FROM ddb_tables WHERE table_name = ?", (table_name,))
        row = cursor.fetchone()
        if not row:
            raise ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": f"Table {table_name} not found"}},
                "PutItem"
            )
        
        hash_key = row[0]
        # Extract the actual value of the partition key from the incoming item data
        # DynamoDB structures look like: {"id": {"S": "user_001"}}
        if hash_key not in item_dict:
            raise ClientError(
                {"Error": {"Code": "ValidationException", "Message": "One or more parameter values were invalid"}},
                "PutItem"
            )
            
        pk_val_wrapper = item_dict[hash_key]
        pk_val = list(pk_val_wrapper.values())[0] # Extracts the actual raw string/number value
        
        # Serialize the entire document structure to text cleanly
        import json
        attributes_json = json.dumps(item_dict)
        
        cursor.execute("""
            INSERT OR REPLACE INTO ddb_items (table_name, partition_key_val, attributes_json)
            VALUES (?, ?, ?)
        """, (table_name, str(pk_val), attributes_json))
        self.conn.commit()

    def get_ddb_item(self, table_name, key_dict):
        cursor = self.conn.cursor()
        cursor.execute("SELECT hash_key FROM ddb_tables WHERE table_name = ?", (table_name,))
        row = cursor.fetchone()
        if not row:
            raise ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": f"Table {table_name} not found"}},
                "GetItem"
            )
            
        hash_key = row[0]
        pk_val = list(key_dict[hash_key].values())[0]
        
        cursor.execute("SELECT attributes_json FROM ddb_items WHERE table_name = ? AND partition_key_val = ?", (table_name, str(pk_val)))
        item_row = cursor.fetchone()
        if not item_row:
            return {} # DynamoDB returns an empty dict response if item doesn't exist
            
        import json
        return json.loads(item_row[0])

    # --- Advanced DynamoDB: Query ---
    def query_ddb_items(self, table_name, expression_values):
        cursor = self.conn.cursor()
        # Extract the lookup token value from DynamoDB structure: {':uid': {'S': 'user_123'}}
        # We find the target lookup value dynamically
        lookup_val = None
        for val_dict in expression_values.values():
            lookup_val = list(val_dict.values())[0]
            break # For simple queries, extract the primary key match value
            
        if not lookup_val:
            raise ClientError(
                {"Error": {"Code": "ValidationException", "Message": "Invalid query parameters"}},
                "Query"
            )

        cursor.execute("""
            SELECT attributes_json FROM ddb_items 
            WHERE table_name = ? AND partition_key_val = ?
        """, (table_name, str(lookup_val)))
        rows = cursor.fetchall()
        
        import json
        return [json.loads(row[0]) for row in rows]

    def delete_object(self, bucket, key):
        cursor = self.conn.cursor()
        cursor.execute("SELECT local_path FROM objects WHERE bucket = ? AND key = ?", (bucket, key))
        row = cursor.fetchone()
        if not row:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
                "DeleteObject"
            )
        local_path = Path(row[0])
        if local_path.exists():
            try:
                local_path.unlink()
            except Exception:
                pass
        cursor.execute("DELETE FROM objects WHERE bucket = ? AND key = ?", (bucket, key))
        self.conn.commit()

    def scan_ddb_items(self, table_name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM ddb_tables WHERE table_name = ?", (table_name,))
        if not cursor.fetchone():
            raise ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": f"Table {table_name} not found"}},
                "Scan"
            )
        cursor.execute("SELECT attributes_json FROM ddb_items WHERE table_name = ?", (table_name,))
        rows = cursor.fetchall()
        import json
        return [json.loads(row[0]) for row in rows]

    def delete_ddb_item(self, table_name, key_dict):
        cursor = self.conn.cursor()
        cursor.execute("SELECT hash_key FROM ddb_tables WHERE table_name = ?", (table_name,))
        row = cursor.fetchone()
        if not row:
            raise ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": f"Table {table_name} not found"}},
                "DeleteItem"
            )
        hash_key = row[0]
        if hash_key not in key_dict:
            raise ClientError(
                {"Error": {"Code": "ValidationException", "Message": "One or more parameter values were invalid"}},
                "DeleteItem"
            )
        pk_val = list(key_dict[hash_key].values())[0]
        cursor.execute("DELETE FROM ddb_items WHERE table_name = ? AND partition_key_val = ?", (table_name, str(pk_val)))
        self.conn.commit()

    def list_ddb_tables(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT table_name FROM ddb_tables")
        return [row[0] for row in cursor.fetchall()]

    # --- S3: CopyObject ---
    def copy_object(self, src_bucket, src_key, dst_bucket, dst_key):
        cursor = self.conn.cursor()
        # Validate source exists
        cursor.execute("SELECT local_path, size FROM objects WHERE bucket = ? AND key = ?", (src_bucket, src_key))
        src_row = cursor.fetchone()
        if not src_row:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
                "CopyObject"
            )
        # Validate destination bucket exists
        cursor.execute("SELECT 1 FROM buckets WHERE name = ?", (dst_bucket,))
        if not cursor.fetchone():
            raise ClientError(
                {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist."}},
                "CopyObject"
            )
        import shutil
        src_path = Path(src_row[0])
        safe_dst = dst_key.replace("/", "___")
        dst_path = self.storage_root / dst_bucket / safe_dst
        shutil.copy2(str(src_path), str(dst_path))
        cursor.execute("""
            INSERT OR REPLACE INTO objects (bucket, key, local_path, size)
            VALUES (?, ?, ?, ?)
        """, (dst_bucket, dst_key, str(dst_path), src_row[1]))
        self.conn.commit()

    # --- S3: DeleteObjects (batch) ---
    def delete_objects_batch(self, bucket, keys):
        deleted = []
        errors = []
        for key in keys:
            try:
                self.delete_object(bucket, key)
                deleted.append(key)
            except ClientError:
                errors.append(key)
        return deleted, errors

    # --- S3: ListBuckets ---
    def list_buckets(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT name, created_at FROM buckets")
        return [{"Name": row[0], "CreationDate": row[1]} for row in cursor.fetchall()]

    # --- S3: HeadObject ---
    def head_object(self, bucket, key):
        cursor = self.conn.cursor()
        cursor.execute("SELECT size, updated_at FROM objects WHERE bucket = ? AND key = ?", (bucket, key))
        row = cursor.fetchone()
        if not row:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
                "HeadObject"
            )
        return {"ContentLength": row[0], "LastModified": row[1]}

    # --- DynamoDB: UpdateItem ---
    def update_ddb_item(self, table_name, key_dict, update_expression, expr_attr_values, expr_attr_names=None):
        import json
        import re
        cursor = self.conn.cursor()
        cursor.execute("SELECT hash_key FROM ddb_tables WHERE table_name = ?", (table_name,))
        row = cursor.fetchone()
        if not row:
            raise ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": f"Table {table_name} not found"}},
                "UpdateItem"
            )
        hash_key = row[0]
        pk_val = list(key_dict[hash_key].values())[0]

        # Fetch existing item or start with a new one containing just the key
        cursor.execute("SELECT attributes_json FROM ddb_items WHERE table_name = ? AND partition_key_val = ?",
                       (table_name, str(pk_val)))
        item_row = cursor.fetchone()
        if item_row:
            item = json.loads(item_row[0])
        else:
            item = dict(key_dict)

        # Parse SET clauses from UpdateExpression
        # Supports: SET #attr = :val, attr = :val
        set_match = re.search(r'SET\s+(.+?)(?:$|REMOVE|ADD|DELETE)', update_expression, re.IGNORECASE)
        if set_match:
            assignments = set_match.group(1).split(',')
            for assignment in assignments:
                parts = assignment.strip().split('=')
                if len(parts) == 2:
                    attr_ref = parts[0].strip()
                    val_ref = parts[1].strip()
                    # Resolve expression attribute names (#name -> actual_name)
                    actual_attr = attr_ref
                    if expr_attr_names and attr_ref in expr_attr_names:
                        actual_attr = expr_attr_names[attr_ref]
                    # Resolve expression attribute values (:val -> typed_value)
                    if val_ref in expr_attr_values:
                        item[actual_attr] = expr_attr_values[val_ref]

        # Parse REMOVE clauses
        remove_match = re.search(r'REMOVE\s+(.+?)(?:$|SET|ADD|DELETE)', update_expression, re.IGNORECASE)
        if remove_match:
            attrs = remove_match.group(1).split(',')
            for attr_ref in attrs:
                attr_ref = attr_ref.strip()
                actual_attr = attr_ref
                if expr_attr_names and attr_ref in expr_attr_names:
                    actual_attr = expr_attr_names[attr_ref]
                item.pop(actual_attr, None)

        cursor.execute("""
            INSERT OR REPLACE INTO ddb_items (table_name, partition_key_val, attributes_json)
            VALUES (?, ?, ?)
        """, (table_name, str(pk_val), json.dumps(item)))
        self.conn.commit()
        return item

    # --- DynamoDB: BatchWriteItem ---
    def batch_write_ddb_items(self, request_items):
        """request_items: {table_name: [{'PutRequest': {'Item': ...}}, {'DeleteRequest': {'Key': ...}}]}"""
        for table_name, operations in request_items.items():
            for op in operations:
                if 'PutRequest' in op:
                    self.put_ddb_item(table_name, op['PutRequest']['Item'])
                elif 'DeleteRequest' in op:
                    try:
                        self.delete_ddb_item(table_name, op['DeleteRequest']['Key'])
                    except ClientError:
                        pass  # BatchWrite silently ignores missing items

    # --- DynamoDB: BatchGetItem ---
    def batch_get_ddb_items(self, request_items):
        """request_items: {table_name: {'Keys': [{'id': {'S': 'val'}}, ...]}}"""
        import json
        results = {}
        for table_name, config in request_items.items():
            keys = config.get('Keys', [])
            items = []
            for key_dict in keys:
                item = self.get_ddb_item(table_name, key_dict)
                if item:
                    items.append(item)
            results[table_name] = items
        return results

    # --- DynamoDB: DescribeTable ---
    def describe_ddb_table(self, table_name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT table_name, hash_key, created_at FROM ddb_tables WHERE table_name = ?", (table_name,))
        row = cursor.fetchone()
        if not row:
            raise ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": f"Table {table_name} not found"}},
                "DescribeTable"
            )
        # Count items
        cursor.execute("SELECT COUNT(*) FROM ddb_items WHERE table_name = ?", (table_name,))
        count = cursor.fetchone()[0]
        return {
            "TableName": row[0],
            "KeySchema": [{"AttributeName": row[1], "KeyType": "HASH"}],
            "TableStatus": "ACTIVE",
            "CreationDateTime": row[2],
            "ItemCount": count,
            "AttributeDefinitions": [{"AttributeName": row[1], "AttributeType": "S"}]
        }

    # --- DynamoDB: DeleteTable ---
    def delete_ddb_table(self, table_name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT hash_key FROM ddb_tables WHERE table_name = ?", (table_name,))
        row = cursor.fetchone()
        if not row:
            raise ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": f"Table {table_name} not found"}},
                "DeleteTable"
            )
        cursor.execute("DELETE FROM ddb_items WHERE table_name = ?", (table_name,))
        cursor.execute("DELETE FROM ddb_tables WHERE table_name = ?", (table_name,))
        self.conn.commit()

    def purge_disk_cache(self):
        """Recursively clears out all cached binary assets on the user's filesystem and database tables"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM objects")
        cursor.execute("DELETE FROM buckets")
        cursor.execute("DELETE FROM ddb_items")
        cursor.execute("DELETE FROM ddb_tables")
        self.conn.commit()
        import shutil
        if self.storage_root.exists():
            # Safely wipe the entire folder contents
            shutil.rmtree(self.storage_root)
            # Re-instantiate the base directory directory so it's ready for future test runs
            self.storage_root.mkdir(parents=True, exist_ok=True)
            print("[MockMesh] Local disk file cache cleared out successfully.")

state_engine = StateEngine()
