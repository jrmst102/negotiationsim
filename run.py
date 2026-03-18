"""Local development runner."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "web.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        reload_dirs=["web", "app"],
    )
