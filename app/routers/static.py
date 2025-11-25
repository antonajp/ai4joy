"""Static File Router for Frontend Assets"""
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse
from pathlib import Path
import os

from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["static"])

# Get the static files directory path
STATIC_DIR = Path(__file__).parent.parent / "static"


@router.get("/static/{file_path:path}")
async def serve_static_file(file_path: str, request: Request):
    """
    Serve static files (CSS, JS, etc.)

    This endpoint serves static assets from the app/static directory.
    """
    # Security check: ensure the requested file is within the static directory
    try:
        file_full_path = (STATIC_DIR / file_path).resolve()
        static_dir_resolved = STATIC_DIR.resolve()

        if not str(file_full_path).startswith(str(static_dir_resolved)):
            logger.warning(
                "Attempted directory traversal",
                requested_path=file_path,
                resolved_path=str(file_full_path)
            )
            return HTMLResponse(content="Not Found", status_code=404)

        if not file_full_path.exists() or not file_full_path.is_file():
            logger.warning("Static file not found", path=file_path)
            return HTMLResponse(content="Not Found", status_code=404)

        # Determine media type based on file extension
        media_types = {
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
        }

        ext = file_full_path.suffix.lower()
        media_type = media_types.get(ext, 'application/octet-stream')

        logger.debug(
            "Serving static file",
            path=file_path,
            media_type=media_type
        )

        return FileResponse(
            path=file_full_path,
            media_type=media_type
        )

    except Exception as e:
        logger.error(
            "Error serving static file",
            path=file_path,
            error=str(e)
        )
        return HTMLResponse(content="Internal Server Error", status_code=500)


@router.get("/")
async def serve_index(request: Request):
    """
    Serve the landing page.

    This endpoint serves the main index.html file at the root path.
    """
    index_path = STATIC_DIR / "index.html"

    if not index_path.exists():
        logger.error("index.html not found", path=str(index_path))
        return HTMLResponse(
            content="<h1>Application Error</h1><p>Landing page not found.</p>",
            status_code=500
        )

    logger.debug("Serving landing page")

    return FileResponse(
        path=index_path,
        media_type="text/html"
    )
