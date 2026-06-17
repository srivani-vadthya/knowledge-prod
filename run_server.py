import os
import sys

port = os.getenv("PORT")
if not port:
    print("ERROR: PORT environment variable not set!")
    sys.exit(1)

print(f"=" * 60)
print(f"Starting Knowledge Assistant API")
print(f"PORT from environment: {port}")
print(f"=" * 60)

os.system(f"uvicorn api:app --host 0.0.0.0 --port {port} --log-level info")
