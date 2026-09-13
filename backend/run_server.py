"""Runner script for launching okDRIVER FastAPI backend server."""

import os
import sys
from pathlib import Path
import uvicorn

# Ensure backend root is on Python path
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Ensure okdriver workspace root is on Python path
WORKSPACE_ROOT = BACKEND_DIR.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() in ("true", "1", "yes")

    print("=" * 60)
    print(f" Starting okDRIVER Pothole Management API Server")
    print(f" Target: http://{host}:{port}")
    print(f" Swagger Documentation: http://localhost:{port}/docs")
    print(f" ReDoc Documentation:   http://localhost:{port}/redoc")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
    )
