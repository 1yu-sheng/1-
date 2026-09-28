import os
import sys

# Load .env if present
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, val = line.split("=", 1)
                if key not in os.environ:
                    os.environ[key] = val

from server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
