import os

import uvicorn


if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("BACKEND_PORT", "8000")))
    # Use full module path for production (FastAPI backend only)
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=port, reload=False)
