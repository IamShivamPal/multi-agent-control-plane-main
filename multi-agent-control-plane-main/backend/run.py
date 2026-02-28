import os

import uvicorn


if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", os.getenv("PORT", "7999")))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
