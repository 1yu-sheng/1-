import os, httpx, json

# Load env
with open(os.path.join(os.path.dirname(os.path.abspath('.')), 'anythingllm_mcp_server', '.env')) as f:
    for line in f:
        line = line.strip()
        if line and '=' in line and not line.startswith('#'):
            key, val = line.split('=', 1)
            if key == 'ANYTHINGLLM_API_KEY':
                api_key = val.strip('"').strip("'")

url = f'http://localhost:3001/api/v1/workspace/531cfcc3-6220-455e-8190-dde1e78e4f44/chat'
resp = httpx.post(url, json={'message': '我的工作区有多少个文件', 'mode': 'chat'}, headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}, timeout=30)
print(f'Status: {resp.status_code}')
print(f'Response: {resp.text[:1000]}')
