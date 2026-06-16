# /Users/aman/mockmesh/mockmesh/automock.py
"""
MockMesh Auto-Mock Compiler Engine

Reads botocore's internal JSON service model schemas at runtime and
generates realistic mock responses automatically for ANY AWS service
operation — without writing a single line of manual handler code.

This transforms MockMesh from a library that supports 21 operations
into one that supports thousands, instantly.
"""
import json
import gzip
import hashlib
import uuid
import time
from pathlib import Path
from datetime import datetime, timezone


class SchemaCompiler:
    """
    Reads botocore service model JSON schemas and compiles
    mock responses on the fly based on the output shape definitions.
    """

    def __init__(self):
        self._service_cache = {}  # Cache loaded service models
        self._botocore_data_dir = self._find_botocore_data()

    def _find_botocore_data(self):
        """Locate botocore's data directory from the installed package"""
        try:
            import botocore
            return Path(botocore.__file__).parent / 'data'
        except ImportError:
            return None

    def _load_service_model(self, service_name):
        """Load and cache a service's JSON schema from botocore's data directory"""
        if service_name in self._service_cache:
            return self._service_cache[service_name]

        if not self._botocore_data_dir:
            return None

        svc_dir = self._botocore_data_dir / service_name
        if not svc_dir.exists():
            return None

        # Find the latest API version
        versions = sorted([d.name for d in svc_dir.iterdir() if d.is_dir()])
        if not versions:
            return None

        latest = versions[-1]
        model_path_gz = svc_dir / latest / 'service-2.json.gz'
        model_path = svc_dir / latest / 'service-2.json'

        try:
            if model_path_gz.exists():
                with gzip.open(model_path_gz, 'rt') as f:
                    model = json.load(f)
            elif model_path.exists():
                model = json.loads(model_path.read_text())
            else:
                return None
        except Exception:
            return None

        self._service_cache[service_name] = model
        return model

    def can_handle(self, service_name, operation_name):
        """Check if we can auto-generate a response for this operation"""
        model = self._load_service_model(service_name)
        if not model:
            return False
        return operation_name in model.get('operations', {})

    def generate_response(self, service_name, operation_name, kwargs=None):
        """
        Generate a complete mock response by walking the output shape tree
        and filling each field with a realistic default value.
        """
        model = self._load_service_model(service_name)
        if not model:
            return self._fallback_response()

        operation = model['operations'].get(operation_name)
        if not operation:
            return self._fallback_response()

        shapes = model.get('shapes', {})

        # Build the response body from the output shape
        output_shape_name = operation.get('output', {}).get('shape')
        if output_shape_name:
            body = self._resolve_shape(output_shape_name, shapes, depth=0, context={
                'service': service_name,
                'operation': operation_name,
                'kwargs': kwargs or {}
            })
        else:
            body = {}

        # Wrap with standard AWS response metadata
        body['ResponseMetadata'] = {
            'HTTPStatusCode': 200,
            'HTTPHeaders': {
                'x-amz-request-id': self._mock_request_id(),
                'content-type': 'application/json',
                'server': 'MockMesh-AutoCompiler'
            }
        }

        return body

    def _resolve_shape(self, shape_name, shapes, depth=0, context=None):
        """
        Recursively walk the shape tree and generate default values.
        Caps recursion at depth 4 to prevent infinite loops on cyclic schemas.
        """
        if depth > 4:
            return None

        shape = shapes.get(shape_name)
        if not shape:
            return None

        shape_type = shape.get('type', 'string')

        if shape_type == 'structure':
            result = {}
            members = shape.get('members', {})
            required = set(shape.get('required', []))
            for member_name, member_def in members.items():
                member_shape = member_def.get('shape', '')
                # Always populate required fields, and top-level fields at depth 0
                if member_name in required or depth == 0:
                    val = self._resolve_shape(member_shape, shapes, depth + 1, context)
                    if val is not None:
                        result[member_name] = val
            return result

        elif shape_type == 'list':
            # Return empty list — the safest default for list responses
            return []

        elif shape_type == 'map':
            return {}

        elif shape_type == 'string':
            return self._generate_string_value(shape_name, shape, context)

        elif shape_type == 'integer' or shape_type == 'long':
            return 0

        elif shape_type == 'float' or shape_type == 'double':
            return 0.0

        elif shape_type == 'boolean':
            return False

        elif shape_type == 'timestamp':
            return datetime.now(timezone.utc).isoformat()

        elif shape_type == 'blob':
            return b''

        else:
            return None

    def _generate_string_value(self, shape_name, shape, context=None):
        """
        Generate realistic string values based on the shape name.
        Uses name pattern matching to produce contextually appropriate values.
        """
        name_lower = shape_name.lower()

        # ARN fields
        if 'arn' in name_lower:
            svc = context.get('service', 'unknown') if context else 'unknown'
            return f"arn:aws:{svc}:us-east-1:123456789012:mockmesh/{uuid.uuid4().hex[:8]}"

        # ID fields
        if name_lower.endswith('id') or 'requestid' in name_lower or 'messageid' in name_lower:
            return uuid.uuid4().hex

        # URL fields
        if 'url' in name_lower or 'endpoint' in name_lower:
            return "https://mockmesh.local/mock-endpoint"

        # Token fields
        if 'token' in name_lower or 'marker' in name_lower:
            return None  # No pagination token = no more pages

        # Status fields
        if 'status' in name_lower or 'state' in name_lower:
            return "ACTIVE"

        # Name fields
        if 'name' in name_lower:
            return "mockmesh-resource"

        # Region
        if 'region' in name_lower:
            return "us-east-1"

        # Account
        if 'account' in name_lower:
            return "123456789012"

        # Hash/checksum fields
        if 'md5' in name_lower or 'checksum' in name_lower or 'etag' in name_lower:
            return hashlib.md5(b"mockmesh").hexdigest()

        # Date fields
        if 'date' in name_lower or 'time' in name_lower or 'created' in name_lower:
            return datetime.now(timezone.utc).isoformat()

        # Enum values — pick the first allowed value
        if 'enum' in shape:
            return shape['enum'][0]

        # Default fallback
        return f"mock-{shape_name}"

    def _mock_request_id(self):
        return f"mockmesh-{uuid.uuid4().hex[:12]}"

    def _fallback_response(self):
        return {
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'HTTPHeaders': {
                    'x-amz-request-id': self._mock_request_id(),
                    'content-type': 'application/json',
                    'server': 'MockMesh-AutoCompiler'
                }
            }
        }

    def get_service_operations(self, service_name):
        """List all operations for a service (useful for dashboard/inspection)"""
        model = self._load_service_model(service_name)
        if not model:
            return []
        return list(model.get('operations', {}).keys())

    def list_available_services(self):
        """List all AWS services available from botocore's data directory"""
        if not self._botocore_data_dir:
            return []
        services = []
        for item in self._botocore_data_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                services.append(item.name)
        return sorted(services)


# Module-level singleton
schema_compiler = SchemaCompiler()
