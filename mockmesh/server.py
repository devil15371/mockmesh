# /Users/aman/mockmesh/mockmesh/server.py
import http.server
import socketserver
import json
import urllib.parse
import threading
from pathlib import Path
from botocore.exceptions import ClientError
from .state import state_engine

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MockMesh Offline Developer Console</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 29, 48, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --primary: #8b5cf6;
            --primary-glow: rgba(139, 92, 246, 0.4);
            --primary-hover: #a78bfa;
            --accent: #6366f1;
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --danger: #ef4444;
            --danger-hover: #f87171;
            --success: #10b981;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Plus Jakarta Sans', sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }

        .glass-panel {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 12px;
        }

        header {
            padding: 1.2rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            background: rgba(11, 15, 25, 0.8);
            backdrop-filter: blur(8px);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .logo-container {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .logo-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 1.1rem;
            box-shadow: 0 0 15px var(--primary-glow);
        }

        .logo-text {
            font-size: 1.4rem;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(to right, #ffffff, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .badge {
            background: rgba(139, 92, 246, 0.15);
            border: 1px solid rgba(139, 92, 246, 0.3);
            color: #c084fc;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .btn {
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            border: none;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.9rem;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--accent));
            color: white;
            box-shadow: 0 4px 12px var(--primary-glow);
        }

        .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 16px var(--primary-glow);
            filter: brightness(1.1);
        }

        .btn-danger {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #f87171;
        }

        .btn-danger:hover {
            background: var(--danger);
            color: white;
            box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
        }

        .container {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 1.5rem;
            flex: 1;
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 2rem;
            width: 100%;
        }

        .sidebar {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .main-content {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            min-width: 0;
        }

        .section-title {
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: var(--text-color);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 0.85rem;
            opacity: 0.8;
        }

        .nav-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
            max-height: 250px;
            overflow-y: auto;
            padding-right: 5px;
        }

        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        .nav-item {
            padding: 0.75rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid transparent;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .nav-item:hover {
            background: rgba(255, 255, 255, 0.03);
            border-color: rgba(255, 255, 255, 0.05);
        }

        .nav-item.active {
            background: rgba(139, 92, 246, 0.1);
            border-color: rgba(139, 92, 246, 0.2);
            color: #d8b4fe;
            font-weight: 500;
        }

        .nav-item-count {
            background: rgba(255, 255, 255, 0.08);
            padding: 0.1rem 0.5rem;
            border-radius: 12px;
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        .active .nav-item-count {
            background: rgba(139, 92, 246, 0.2);
            color: #d8b4fe;
        }

        .panel-padding {
            padding: 1.5rem;
        }

        .empty-state {
            text-align: center;
            padding: 4rem 2rem;
            color: var(--text-muted);
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1rem;
        }

        .empty-state-icon {
            font-size: 2.5rem;
            opacity: 0.5;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        th {
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-muted);
            font-weight: 500;
            font-size: 0.85rem;
            text-transform: uppercase;
        }

        td {
            padding: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            font-size: 0.95rem;
            vertical-align: middle;
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.01);
        }

        .mono-text {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            background: rgba(255, 255, 255, 0.05);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
        }

        .action-icon {
            cursor: pointer;
            padding: 0.4rem;
            border-radius: 6px;
            background: transparent;
            border: 1px solid transparent;
            color: var(--text-muted);
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .action-icon:hover {
            color: var(--danger);
            background: rgba(239, 68, 68, 0.1);
            border-color: rgba(239, 68, 68, 0.2);
        }

        .action-icon-download:hover {
            color: var(--success);
            background: rgba(16, 185, 129, 0.1);
            border-color: rgba(16, 185, 129, 0.2);
        }

        .toast {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            background: #161d30;
            border-left: 4px solid var(--primary);
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            gap: 0.75rem;
            transform: translateY(150%);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 1000;
        }

        .toast.show {
            transform: translateY(0);
        }

        .json-preview {
            background: #0d1117;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem;
            overflow-x: auto;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            max-height: 400px;
            margin-top: 0.5rem;
        }
    </style>
</head>
<body>

    <header>
        <div class="logo-container">
            <div class="logo-icon">M</div>
            <div class="logo-text">MockMesh</div>
            <span class="badge">Local Console</span>
        </div>
        <div style="display: flex; align-items: center; gap: 1.5rem;">
            <div style="font-size: 0.9rem; color: var(--text-muted)">
                Endpoint: <span class="mono-text" style="color: #c084fc">http://localhost:4566</span>
            </div>
            <button class="btn btn-danger" onclick="triggerWipe()">
                Reset System State
            </button>
        </div>
    </header>

    <div class="container">
        <div class="sidebar">
            <div class="glass-panel panel-padding">
                <h3 class="section-title">S3 Buckets</h3>
                <ul class="nav-list" id="s3-bucket-list"></ul>
            </div>
            <div class="glass-panel panel-padding">
                <h3 class="section-title">DynamoDB Tables</h3>
                <ul class="nav-list" id="ddb-table-list"></ul>
            </div>
        </div>

        <div class="main-content">
            <div class="glass-panel panel-padding" id="detail-panel" style="min-height: 400px;">
                <div class="empty-state">
                    <div class="empty-state-icon">☁️</div>
                    <h2>No Resource Selected</h2>
                    <p>Select a bucket or table from the sidebar to inspect items, download S3 objects, or query DynamoDB values.</p>
                </div>
            </div>
        </div>
    </div>

    <div class="toast" id="toast-message">
        <svg width="18" height="18" fill="none" stroke="var(--success)" stroke-width="2" viewBox="0 0 24 24"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke-linecap="round" stroke-linejoin="round"/></svg>
        <span id="toast-text">State purged successfully.</span>
    </div>

    <script>
        let localState = { s3: { buckets: [], objects: [] }, dynamodb: { tables: [], items: [] } };
        let activeResource = null;

        async function fetchState() {
            try {
                const res = await fetch('/_api/state');
                if (res.ok) {
                    localState = await res.json();
                    renderSidebar();
                    renderDetail();
                }
            } catch (err) {
                console.error("Failed to sync mockmesh state:", err);
            }
        }

        function showToast(msg) {
            const toast = document.getElementById('toast-message');
            document.getElementById('toast-text').innerText = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }

        async function triggerWipe() {
            if (confirm("Are you sure you want to delete all local tables, items, buckets, and physical S3 files? This cannot be undone.")) {
                try {
                    const res = await fetch('/_api/clean', { method: 'POST' });
                    if (res.ok) {
                        showToast("System state reset successfully!");
                        activeResource = null;
                        await fetchState();
                    }
                } catch (err) {
                    showToast("Error resetting state.");
                }
            }
        }

        async function deleteS3Object(bucket, key) {
            if (confirm(`Delete key "${key}"?`)) {
                try {
                    const res = await fetch(`/${bucket}/${key}`, { method: 'DELETE' });
                    if (res.ok) {
                        showToast("File deleted.");
                        await fetchState();
                    }
                } catch (err) {
                    showToast("Failed to delete object.");
                }
            }
        }

        async function deleteDdbItem(tableName, keyVal) {
            if (confirm(`Delete DynamoDB item with PK "${keyVal}"?`)) {
                try {
                    const res = await fetch('/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Amz-Target': 'DynamoDB_20120810.DeleteItem'
                        },
                        body: JSON.stringify({
                            TableName: tableName,
                            Key: {
                                [getTableHashKey(tableName)]: { S: keyVal }
                            }
                        })
                    });
                    if (res.ok) {
                        showToast("Item deleted.");
                        await fetchState();
                    }
                } catch (err) {
                    showToast("Failed to delete item.");
                }
            }
        }

        function getTableHashKey(tableName) {
            const tbl = localState.dynamodb.tables.find(t => t.table_name === tableName);
            return tbl ? tbl.hash_key : 'id';
        }

        function selectResource(type, name) {
            activeResource = { type, name };
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            const activeEl = document.getElementById(`nav-${type}-${name}`);
            if (activeEl) activeEl.classList.add('active');
            renderDetail();
        }

        function renderSidebar() {
            const s3List = document.getElementById('s3-bucket-list');
            if (localState.s3.buckets.length === 0) {
                s3List.innerHTML = '<li style="color:var(--text-muted);font-size:0.85rem;padding:0.5rem 0;">No buckets created</li>';
            } else {
                s3List.innerHTML = localState.s3.buckets.map(b => {
                    const objCount = localState.s3.objects.filter(o => o.bucket === b.name).length;
                    const isActive = activeResource && activeResource.type === 's3' && activeResource.name === b.name;
                    return `
                        <li class="nav-item ${isActive ? 'active' : ''}" id="nav-s3-${b.name}" onclick="selectResource('s3', '${b.name}')">
                            <span>🪣 ${b.name}</span>
                            <span class="nav-item-count">${objCount}</span>
                        </li>
                    `;
                }).join('');
            }

            const ddbList = document.getElementById('ddb-table-list');
            if (localState.dynamodb.tables.length === 0) {
                ddbList.innerHTML = '<li style="color:var(--text-muted);font-size:0.85rem;padding:0.5rem 0;">No tables created</li>';
            } else {
                ddbList.innerHTML = localState.dynamodb.tables.map(t => {
                    const itemCount = localState.dynamodb.items.filter(i => i.table_name === t.table_name).length;
                    const isActive = activeResource && activeResource.type === 'ddb' && activeResource.name === t.table_name;
                    return `
                        <li class="nav-item ${isActive ? 'active' : ''}" id="nav-ddb-${t.table_name}" onclick="selectResource('ddb', '${t.table_name}')">
                            <span>⚡ ${t.table_name}</span>
                            <span class="nav-item-count">${itemCount}</span>
                        </li>
                    `;
                }).join('');
            }
        }

        function renderDetail() {
            const panel = document.getElementById('detail-panel');
            if (!activeResource) {
                panel.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">☁️</div>
                        <h2>No Resource Selected</h2>
                        <p>Select a bucket or table from the sidebar to inspect items, download S3 objects, or query DynamoDB values.</p>
                    </div>
                `;
                return;
            }

            if (activeResource.type === 's3') {
                const bucketName = activeResource.name;
                const objects = localState.s3.objects.filter(o => o.bucket === bucketName);

                let rowsHtml = '';
                if (objects.length === 0) {
                    rowsHtml = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);padding:3rem 0;">Bucket is empty</td></tr>';
                } else {
                    rowsHtml = objects.map(o => {
                        return `
                            <tr>
                                <td class="mono-text">${o.key}</td>
                                <td>${(o.size / 1024).toFixed(2)} KB</td>
                                <td style="color:var(--text-muted);font-size:0.85rem;">${o.updated_at}</td>
                                <td style="text-align:right;">
                                    <a href="/${bucketName}/${o.key}" target="_blank" class="action-icon action-icon-download" title="Download payload">
                                        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" stroke-linecap="round" stroke-linejoin="round"/></svg>
                                    </a>
                                    <button class="action-icon" onclick="deleteS3Object('${bucketName}', '${o.key}')" title="Delete object">
                                        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" stroke-linecap="round" stroke-linejoin="round"/></svg>
                                    </button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }

                panel.innerHTML = `
                    <div style="display:flex;justify-content:between;align-items:center;margin-bottom:1.5rem;">
                        <div>
                            <h2 style="font-size:1.5rem;font-weight:700;">Bucket: ${bucketName}</h2>
                            <p style="color:var(--text-muted);font-size:0.9rem;">S3 storage object listing</p>
                        </div>
                    </div>
                    <div style="overflow-x:auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Object Key</th>
                                    <th>Size</th>
                                    <th>Last Modified</th>
                                    <th style="text-align:right;">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rowsHtml}
                            </tbody>
                        </table>
                    </div>
                `;
            } else if (activeResource.type === 'ddb') {
                const tableName = activeResource.name;
                const items = localState.dynamodb.items.filter(i => i.table_name === tableName);
                const hashKey = getTableHashKey(tableName);

                let rowsHtml = '';
                if (items.length === 0) {
                    rowsHtml = '<tr><td colspan="3" style="text-align:center;color:var(--text-muted);padding:3rem 0;">Table contains no documents</td></tr>';
                } else {
                    rowsHtml = items.map((item, idx) => {
                        const parsedAttrs = JSON.parse(item.attributes_json);
                        const pkVal = item.partition_key_val;
                        return `
                            <tr>
                                <td class="mono-text" style="font-weight:600;color:#c084fc;">${pkVal}</td>
                                <td>
                                    <button class="btn" style="padding:0.3rem 0.6rem;font-size:0.8rem;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);" onclick="toggleJson(${idx})">Toggle Document JSON</button>
                                    <div id="json-preview-${idx}" class="json-preview" style="display:none;">
                                        <pre>${JSON.stringify(parsedAttrs, null, 2)}</pre>
                                    </div>
                                </td>
                                <td style="text-align:right;">
                                    <button class="action-icon" onclick="deleteDdbItem('${tableName}', '${pkVal}')" title="Delete record">
                                        <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" stroke-linecap="round" stroke-linejoin="round"/></svg>
                                    </button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }

                panel.innerHTML = `
                    <div style="display:flex;justify-content:between;align-items:center;margin-bottom:1.5rem;">
                        <div>
                            <h2 style="font-size:1.5rem;font-weight:700;">Table: ${tableName}</h2>
                            <p style="color:var(--text-muted);font-size:0.9rem;">DynamoDB items listing (Partition Key: <span class="mono-text">${hashKey}</span>)</p>
                        </div>
                    </div>
                    <div style="overflow-x:auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Partition Key Value</th>
                                    <th>Document attributes</th>
                                    <th style="text-align:right;">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rowsHtml}
                            </tbody>
                        </table>
                    </div>
                `;
            }
        }

        function toggleJson(idx) {
            const preview = document.getElementById(`json-preview-${idx}`);
            if (preview.style.display === 'none') {
                preview.style.display = 'block';
            } else {
                preview.style.display = 'none';
            }
        }

        fetchState();
        setInterval(fetchState, 3000);
    </script>
</body>
</html>
"""


class MockMeshHTTPHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default terminal request output log spam
        pass

    def _send_xml(self, status, xml_body):
        self.send_response(status)
        self.send_header('Content-Type', 'application/xml')
        encoded = xml_body.encode('utf-8')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, status, data, headers=None):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        body = json.dumps(data).encode('utf-8')
        self.send_header('Content-Length', str(len(body)))
        if headers:
            for k, v in headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, service, error):
        code = error.response['Error']['Code']
        message = error.response['Error']['Message']
        
        if service == 's3':
            status = 400
            if code in ('NoSuchKey', 'NoSuchBucket'):
                status = 404
            elif code == 'BucketAlreadyExists':
                status = 409
            
            xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Error>
    <Code>{code}</Code>
    <Message>{message}</Message>
    <RequestId>MOCKMESH123456789</RequestId>
</Error>"""
            self._send_xml(status, xml)
        else:
            headers = {
                'x-amzn-ErrorType': f"com.amazonaws.dynamodb.v20120810#{code}"
            }
            res = {
                "__type": f"com.amazonaws.dynamodb.v20120810#{code}",
                "message": message
            }
            self._send_json(400, res, headers=headers)

    def parse_s3_path(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        parts = [p for p in path.split('/') if p]
        
        host = self.headers.get('Host', '')
        host_name = host.split(':')[0]
        
        if (host_name.endswith('.localhost') or 
            '.s3.' in host_name or 
            host_name.endswith('.amazonaws.com')):
            subdomains = host_name.split('.')
            if len(subdomains) > 1:
                bucket = subdomains[0]
                key = path.lstrip('/')
                return bucket, key

        if len(parts) >= 1:
            bucket = parts[0]
            key = '/'.join(parts[1:]) if len(parts) > 1 else ""
            return bucket, key
            
        return None, ""

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path in ('/dashboard', '/dashboard/', '/dashboard/index.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(DASHBOARD_HTML)))
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode('utf-8'))
            return
            
        if path == '/_api/state':
            cursor = state_engine.conn.cursor()
            
            cursor.execute("SELECT name, created_at FROM buckets")
            buckets = [{"name": r[0], "created_at": r[1]} for r in cursor.fetchall()]
            
            cursor.execute("SELECT bucket, key, size, updated_at FROM objects")
            objects = [{"bucket": r[0], "key": r[1], "size": r[2], "updated_at": r[3]} for r in cursor.fetchall()]
            
            cursor.execute("SELECT table_name, hash_key, created_at FROM ddb_tables")
            ddb_tables = [{"table_name": r[0], "hash_key": r[1], "created_at": r[2]} for r in cursor.fetchall()]
            
            cursor.execute("SELECT table_name, partition_key_val, attributes_json FROM ddb_items")
            ddb_items = [{"table_name": r[0], "partition_key_val": r[1], "attributes_json": r[2]} for r in cursor.fetchall()]
            
            self._send_json(200, {
                "s3": {
                    "buckets": buckets,
                    "objects": objects
                },
                "dynamodb": {
                    "tables": ddb_tables,
                    "items": ddb_items
                }
            })
            return
            
        bucket, key = self.parse_s3_path()
        if not bucket:
            # Fallback redirect to dashboard
            self.send_response(302)
            self.send_header('Location', '/dashboard')
            self.end_headers()
            return
            
        try:
            if key == "":
                query_params = urllib.parse.parse_qs(parsed_url.query)
                prefix = query_params.get('prefix', [''])[0]
                
                obj_list = state_engine.list_s3_objects(bucket, prefix)
                
                contents_xml = ""
                for obj in obj_list:
                    contents_xml += f"""    <Contents>
        <Key>{obj['Key']}</Key>
        <LastModified>{obj['LastModified']}</LastModified>
        <ETag>"{obj['Key']}"</ETag>
        <Size>{obj['Size']}</Size>
        <StorageClass>STANDARD</StorageClass>
    </Contents>"""
                
                xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <Name>{bucket}</Name>
    <Prefix>{prefix}</Prefix>
    <KeyCount>{len(obj_list)}</KeyCount>
    <MaxKeys>1000</MaxKeys>
    <IsTruncated>false</IsTruncated>
{contents_xml}
</ListBucketResult>"""
                self._send_xml(200, xml)
            else:
                data = state_engine.get_object(bucket, key)
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except ClientError as ce:
            self._send_error('s3', ce)

    def do_PUT(self):
        bucket, key = self.parse_s3_path()
        if not bucket:
            self.send_response(400)
            self.end_headers()
            return
            
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(content_length)
            
            if key == "":
                state_engine.create_bucket(bucket)
                self.send_response(200)
                self.end_headers()
            else:
                state_engine.put_object(bucket, key, data)
                self.send_response(200)
                self.send_header('ETag', f'"{key}"')
                self.end_headers()
        except ClientError as ce:
            self._send_error('s3', ce)

    def do_DELETE(self):
        bucket, key = self.parse_s3_path()
        if not bucket or key == "":
            self.send_response(400)
            self.end_headers()
            return
            
        try:
            state_engine.delete_object(bucket, key)
            self.send_response(204)
            self.end_headers()
        except ClientError as ce:
            self._send_error('s3', ce)

    def do_HEAD(self):
        bucket, key = self.parse_s3_path()
        if not bucket:
            self.send_response(400)
            self.end_headers()
            return
            
        try:
            cursor = state_engine.conn.cursor()
            if key == "":
                cursor.execute("SELECT 1 FROM buckets WHERE name = ?", (bucket,))
                if not cursor.fetchone():
                    raise ClientError(
                        {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist."}},
                        "HeadBucket"
                    )
                self.send_response(200)
                self.end_headers()
            else:
                cursor.execute("SELECT size FROM objects WHERE bucket = ? AND key = ?", (bucket, key))
                row = cursor.fetchone()
                if not row:
                    raise ClientError(
                        {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
                        "HeadObject"
                    )
                self.send_response(200)
                self.send_header('Content-Length', str(row[0]))
                self.end_headers()
        except ClientError as ce:
            self._send_error('s3', ce)

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == '/_api/clean':
            state_engine.purge_disk_cache()
            self._send_json(200, {"status": "success", "message": "Cache wiped successfully"})
            return
            
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        target = self.headers.get('X-Amz-Target', '')
        if not target:
            self.send_response(400)
            self.end_headers()
            return
            
        operation = target.split('.')[-1]
        try:
            req_data = json.loads(body) if body else {}
        except Exception:
            req_data = {}
            
        table_name = req_data.get('TableName')
        
        try:
            if operation == 'CreateTable':
                hash_key = req_data['KeySchema'][0]['AttributeName']
                state_engine.create_ddb_table(table_name, hash_key)
                res = {
                    "TableDescription": {
                        "TableName": table_name,
                        "TableStatus": "ACTIVE",
                        "ItemCount": 0
                    }
                }
                self._send_json(200, res)
                
            elif operation == 'PutItem':
                item = req_data['Item']
                state_engine.put_ddb_item(table_name, item)
                self._send_json(200, {})
                
            elif operation == 'GetItem':
                key = req_data['Key']
                item_data = state_engine.get_ddb_item(table_name, key)
                res = {}
                if item_data:
                    res["Item"] = item_data
                self._send_json(200, res)
                
            elif operation == 'Query':
                val_attrs = req_data.get('ExpressionAttributeValues', {})
                items = state_engine.query_ddb_items(table_name, val_attrs)
                res = {
                    "Items": items,
                    "Count": len(items),
                    "ScannedCount": len(items)
                }
                self._send_json(200, res)
                
            elif operation == 'Scan':
                items = state_engine.scan_ddb_items(table_name)
                res = {
                    "Items": items,
                    "Count": len(items),
                    "ScannedCount": len(items)
                }
                self._send_json(200, res)
                
            elif operation == 'DeleteItem':
                key = req_data['Key']
                state_engine.delete_ddb_item(table_name, key)
                self._send_json(200, {})
                
            elif operation == 'ListTables':
                tables = state_engine.list_ddb_tables()
                res = {
                    "TableNames": tables
                }
                self._send_json(200, res)
                
            else:
                self.send_response(404)
                self.end_headers()
        except ClientError as ce:
            self._send_error('dynamodb', ce)


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


_server_instance = None
_server_thread = None

def start_server(port=4566, block=False):
    global _server_instance, _server_thread
    server_address = ('', port)
    _server_instance = ThreadingHTTPServer(server_address, MockMeshHTTPHandler)
    
    print(f"\n🚀 [MockMesh Standalone Server] Active at http://localhost:{port}")
    print(f"📊 [MockMesh Dev Console] Open http://localhost:{port}/dashboard in your browser")
    
    if block:
        try:
            _server_instance.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down MockMesh server gracefully...")
            _server_instance.server_close()
    else:
        _server_thread = threading.Thread(target=_server_instance.serve_forever, daemon=True)
        _server_thread.start()

def stop_server():
    global _server_instance
    if _server_instance:
        _server_instance.shutdown()
        _server_instance.server_close()
        _server_instance = None
        print("[MockMesh Standalone Server] Stopped.")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="MockMesh CLI: Standalone local AWS emulating engine")
    parser.add_argument('command', choices=['start'], help="Command to run: 'start'")
    parser.add_argument('--port', type=int, default=4566, help="Port to listen on (default: 4566)")
    
    args = parser.parse_args()
    if args.command == 'start':
        start_server(port=args.port, block=True)

if __name__ == '__main__':
    main()
